#!/usr/bin/env python3
"""Local stock-pitch dashboard. Python 3.9+; standard library only."""
import argparse
import concurrent.futures
from datetime import datetime, date, time, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import sys
from pathlib import Path
import threading
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data' / 'prices.json'
LOCK = threading.RLock()
STATE = {'running': False, 'completed': 0, 'total': 0, 'lastError': None}
SNAPSHOT = None

def resource():
    return json.loads((ROOT / 'resources' / 'stocks.json').read_text())

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0

def cutoff_date():
    return (datetime.now(ZoneInfo('Asia/Seoul')).date() - timedelta(days=1)).isoformat()

def calculate(stock, purchase_date, chart, as_of_date=None):
    as_of_date = as_of_date or cutoff_date()
    tz = ZoneInfo('Asia/Seoul' if stock['market'] == 'KR' else 'America/New_York')
    meta = chart['meta']
    if meta.get('currency') != stock['currency']:
        raise ValueError('조회 통화가 종목 리소스와 다릅니다')
    now = datetime.now(timezone.utc).timestamp()
    quotes = chart['indicators']['quote'][0]['close']
    points = []
    for stamp, close in zip(chart.get('timestamp', []), quotes):
        day = datetime.fromtimestamp(stamp, tz).date()
        closing_time = time(15, 30) if stock['market'] == 'KR' else time(16, 0)
        closed_at = datetime.combine(day, closing_time, tzinfo=tz).timestamp()
        if day.isoformat() <= as_of_date and closed_at <= now and finite(close):
            points.append({'date': day.isoformat(), 'price': round(close, 2), 'timestamp': closed_at})
    points.sort(key=lambda p: p['timestamp'])
    base = next((p for p in points if p['date'] == purchase_date), None)
    result = {'symbol': stock['symbol'], 'fetchedAt': utcnow(), 'source': 'Yahoo Finance', 'sourceUrl': 'https://finance.yahoo.com/quote/' + urllib.parse.quote(stock['symbol'], safe=''), 'basePrice': None, 'currentPrice': None, 'returnPct': None, 'history': [], 'asOf': None, 'status': 'unavailable', 'message': ''}
    if not base:
        result['message'] = purchase_date + ' 종가가 제공되지 않습니다'
        return result
    # Yahoo historical closes already reflect subsequent splits. Recover the
    # original purchase close for display; compare prices on the same basis.
    splits = []
    for split in chart.get('events', {}).get('splits', {}).values():
        day = datetime.fromtimestamp(split['date'], tz).date().isoformat()
        if purchase_date < day <= as_of_date and split['date'] <= now:
            splits.append((day, float(split['numerator']) / float(split['denominator'])))
    def factor(day):
        return math.prod(f for d, f in splits if d <= day)
    history = [{'date': p['date'], 'returnPct': (p['price'] / base['price'] - 1) * 100} for p in points if p['date'] >= purchase_date]
    latest = next((p for p in reversed(points) if p['date'] >= purchase_date), base)
    price, stamp = latest['price'], latest['timestamp']
    day = datetime.fromtimestamp(stamp, tz).date().isoformat()
    ret = (price / base['price'] - 1) * 100
    if history and history[-1]['date'] == day:
        history[-1]['returnPct'] = ret
    else:
        history.append({'date': day, 'returnPct': ret})
    result.update(basePrice=base['price'] * factor(day), currentPrice=price, returnPct=ret, history=history, priceDate=day, asOf=datetime.fromtimestamp(stamp, timezone.utc).isoformat(), status='ok', splitFactor=factor(day), message='')
    return result

def fetch_stock(stock, purchase_date, as_of_date=None):
    as_of_date = as_of_date or cutoff_date()
    tz = ZoneInfo('Asia/Seoul' if stock['market'] == 'KR' else 'America/New_York')
    start = int(datetime.combine(date.fromisoformat(purchase_date) - timedelta(days=3), time.min, tzinfo=tz).timestamp())
    end = int(datetime.combine(date.fromisoformat(as_of_date) + timedelta(days=1), time.min, tzinfo=tz).timestamp())
    params = urllib.parse.urlencode({'period1': start, 'period2': max(end, start+86400), 'interval': '1d', 'events': 'splits', 'includePrePost': 'false'})
    errors = []
    for host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']:
        try:
            url = 'https://' + host + '/v8/finance/chart/' + urllib.parse.quote(stock['symbol'], safe='') + '?' + params
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.load(response)
            chart = data['chart']
            if chart.get('error') or not chart.get('result'):
                raise ValueError(str(chart.get('error', '가격 없음')))
            return calculate(stock, purchase_date, chart['result'][0], as_of_date)
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError('; '.join(errors))

def refresh(as_of_date=None):
    global SNAPSHOT
    try:
        config = resource()
        as_of_date = as_of_date or cutoff_date()
        old = {r['symbol']: r for r in (SNAPSHOT or {}).get('quotes', []) if r.get('priceDate', '9999') <= as_of_date} if (SNAPSHOT or {}).get('purchaseDate') == config['purchaseDate'] and (SNAPSHOT or {}).get('priceMode') == 'previous_close' else {}
        rows = []
        with LOCK:
            STATE.update(completed=0, total=len(config['stocks']), lastError=None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            jobs = {pool.submit(fetch_stock, s, config['purchaseDate'], as_of_date): s for s in config['stocks']}
            for future in concurrent.futures.as_completed(jobs):
                stock = jobs[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = dict(old.get(stock['symbol'], {'symbol': stock['symbol'], 'basePrice': None, 'currentPrice': None, 'returnPct': None, 'history': [], 'asOf': None}))
                    row.update(status='stale' if row.get('currentPrice') is not None else 'error', message='가격 조회 실패: ' + str(exc))
                rows.append(row)
                with LOCK:
                    STATE['completed'] += 1
        order = {s['symbol']: i for i, s in enumerate(config['stocks'])}
        rows.sort(key=lambda row: order[row['symbol']])
        if not any(r.get('status') == 'ok' for r in rows):
            raise ValueError('全 종목 조회 실패: 기존 가격 파일을 유지합니다')
        result = {'purchaseDate': config['purchaseDate'], 'asOfDate': as_of_date, 'priceMode': 'previous_close', 'updatedAt': utcnow(), 'quotes': rows}
        CACHE.parent.mkdir(exist_ok=True)
        temp = CACHE.with_suffix('.tmp')
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        temp.replace(CACHE)
        with LOCK:
            SNAPSHOT = result
    except Exception as exc:
        with LOCK:
            STATE['lastError'] = str(exc)
    finally:
        with LOCK:
            STATE['running'] = False

def start_refresh():
    with LOCK:
        if STATE['running']:
            return False
        STATE.update(running=True, completed=0, total=len(resource()['stocks']))
    threading.Thread(target=refresh, daemon=True).start()
    return True

class Handler(SimpleHTTPRequestHandler):
    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == '/api/prices':
            with LOCK:
                self.json_response({'snapshot': SNAPSHOT, 'refresh': dict(STATE)})
        elif path == '/api/resource':
            self.json_response(resource())
        elif path in ['/', '/index.html', '/style.css', '/app.js', '/resources/stocks.json', '/data/prices.json']:
            super().do_GET()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != '/api/refresh':
            return self.send_error(404)
        # Refresh is a local UI operation, not a cross-origin endpoint.
        origin = self.headers.get('Origin')
        if origin and urllib.parse.urlsplit(origin).netloc != self.headers.get('Host'):
            return self.send_error(403)
        start_refresh()
        self.json_response({'accepted': True}, 202)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--refresh', action='store_true', help='가격 캐시만 갱신하고 종료')
    parser.add_argument('--as-of', help='종가의 마지막 거래일 상한 (YYYY-MM-DD); 기본값은 한국시간 전일')
    args = parser.parse_args()
    if CACHE.exists():
        try:
            SNAPSHOT = json.loads(CACHE.read_text())
            if SNAPSHOT.get('purchaseDate') != resource()['purchaseDate']:
                SNAPSHOT = None
        except (ValueError, OSError):
            pass
    if args.refresh:
        refresh(args.as_of)
        print(json.dumps({'refresh': STATE, 'valid': sum(r.get('returnPct') is not None for r in (SNAPSHOT or {}).get('quotes', []))}, ensure_ascii=False))
        sys.exit(1 if STATE['lastError'] else 0)
    else:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
        print(f'대시보드: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
