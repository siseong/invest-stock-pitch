import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
import server

def stamp(day, hour=14, minute=30):
    return int(datetime.fromisoformat(f'{day}T{hour:02d}:{minute:02d}:00+00:00').timestamp())

class ClosingPriceTests(unittest.TestCase):
    stock = {'symbol': 'TEST', 'market': 'US', 'currency': 'USD'}
    def chart(self, values):
        return {'meta': {'currency': 'USD', 'regularMarketPrice': 99999, 'regularMarketTime': stamp('2026-11-13')}, 'timestamp': [stamp(d) for d, _ in values], 'indicators': {'quote': [{'close': [v for _, v in values]}]}}
    def test_cutoff_excludes_later_session_and_live_quote(self):
        r = server.calculate(self.stock, '2026-11-10', self.chart([('2026-11-10', 100), ('2026-11-11', 105), ('2026-11-12', 110), ('2026-11-13', 120)]), '2026-11-12')
        self.assertEqual(r['currentPrice'], 110)
        self.assertAlmostEqual(r['returnPct'], 10)
        self.assertEqual(r['priceDate'], '2026-11-12')
        self.assertEqual(r['asOf'], '2026-11-12T21:00:00+00:00')
    def test_no_replacement_for_missing_purchase_close(self):
        r = server.calculate(self.stock, '2026-11-10', self.chart([('2026-11-11', 105)]), '2026-11-12')
        self.assertEqual(r['status'], 'unavailable')
        self.assertIsNone(r['returnPct'])
    def test_holiday_uses_last_trading_close(self):
        r = server.calculate(self.stock, '2026-11-10', self.chart([('2026-11-10', 100), ('2026-11-12', 110)]), '2026-11-14')
        self.assertEqual(r['priceDate'], '2026-11-12')
    def test_split_not_counted_twice(self):
        chart = self.chart([('2026-11-10', 50), ('2026-11-12', 55)])
        chart['events'] = {'splits': {'s': {'date': stamp('2026-11-12'), 'numerator': 2, 'denominator': 1}}}
        r = server.calculate(self.stock, '2026-11-10', chart, '2026-11-12')
        self.assertEqual(r['basePrice'], 100)
        self.assertEqual(r['splitFactor'], 2)
        self.assertAlmostEqual(r['returnPct'], 10)
    def test_purchase_day_not_yet_in_daily_cutoff(self):
        r = server.calculate(self.stock, '2026-11-12', self.chart([('2026-11-12', 100)]), '2026-11-11')
        self.assertEqual(r['status'], 'pending')
        self.assertEqual(r['basePrice'], 100)
        self.assertIsNone(r['returnPct'])
    def test_public_resource_has_counts_only(self):
        data = server.resource()
        self.assertEqual(data['purchaseDate'], '2026-11-13')
        self.assertEqual(sum(s['selectionCount'] for s in data['stocks']), 41)
        self.assertEqual(next(s for s in data['stocks'] if s['symbol']=='NVDA')['selectionCount'], 2)
        for stock in data['stocks']:
            self.assertNotIn('presenters', stock)
            self.assertNotIn('sources', stock)
    def test_refresh_keeps_benchmarks_out_of_stock_rows(self):
        config = {'purchaseDate': '2026-11-13', 'stocks': [self.stock], 'benchmarks': [{'symbol':'^GSPC','market':'US','currency':'USD'}]}
        def fake_fetch(asset, *args):
            return {'symbol':asset['symbol'], 'status':'pending', 'returnPct':None, 'history':[]}
        with tempfile.TemporaryDirectory() as temp, patch.object(server,'resource',return_value=config), patch.object(server,'fetch_stock',side_effect=fake_fetch), patch.object(server,'CACHE',Path(temp)/'prices.json'), patch.object(server,'SNAPSHOT',None):
            server.refresh('2026-11-12')
            data = json.loads((Path(temp)/'prices.json').read_text())
            self.assertEqual([r['symbol'] for r in data['quotes']], ['TEST'])
            self.assertEqual([r['symbol'] for r in data['benchmarks']], ['^GSPC'])
    def test_currency_mismatch(self):
        chart = self.chart([('2026-11-10', 100)])
        chart['meta']['currency'] = 'EUR'
        with self.assertRaises(ValueError):
            server.calculate(self.stock, '2026-11-10', chart, '2026-11-12')
    def test_price_precision(self):
        r = server.calculate(self.stock, '2026-11-10', self.chart([('2026-11-10', 166.19000244), ('2026-11-12', 166.19)]), '2026-11-12')
        self.assertEqual(r['returnPct'], 0)

if __name__ == '__main__':
    unittest.main()
