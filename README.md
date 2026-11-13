# EMBA Stock Pitch · 종목별 성과

40명의 발표자가 선택한 38개 고유 종목을 비교하는 대시보드입니다. 종목별 성과 표를 맨 위에 표시합니다.

- 사이트: https://siseong.github.io/invest-stock-pitch/
- 종목 목록: [`resources/stocks.json`](resources/stocks.json)
- 가격 스냅샷: [`data/prices.json`](data/prices.json)
- 워크플로: [Update closing prices and deploy Pages](../../actions/workflows/update-and-deploy.yml)

## 수익률 기준

**2026-11-12 각 시장 정규장 종가 매수**를 가정합니다. `(전일 종가 / 매수 종가 - 1) × 100`으로 계산하며, 주식분할은 수량 변화를 반영합니다. 배당, 환율, 거래비용은 제외합니다. 전체 평균은 가격을 확인한 고유 종목에 동일 비중을 적용합니다.

전일은 한국시간 기준 어제입니다. 한국·미국 모두 그 날짜까지 마감된 마지막 정규장 일봉 종가만 사용합니다. 휴장일은 마지막 거래일 종가를 유지하며, 장중·장외 가격은 사용하지 않습니다. 매수일 종가가 없으면 다른 날짜로 대체하지 않습니다. 표의 가격 기준 시각은 KST로 표시합니다.

## 매일 오전 8시 자동 업데이트

GitHub Actions가 매일 **08:00 Asia/Seoul (23:00 UTC)**에 가격을 수집하고 JSON을 커밋한 뒤 GitHub Pages에 배포합니다. 사용자 컴퓨터가 켜져 있지 않아도 실행됩니다. GitHub의 예약 실행 특성상 시작 시각이 지연될 수 있습니다. 공개 저장소가 장기간 활동이 없으면 예약 실행이 비활성화될 수 있으므로 Actions 상태를 확인하세요.

Actions의 **Run workflow**로 즉시 갱신할 수 있습니다. 종목 추가·수정 또는 화면 변경을 main에 올리면 같은 검증·갱신·배포가 실행됩니다. 데이터 커밋은 동일 실행에서 배포하여 GITHUB_TOKEN 커밋의 재귀 트리거에 의존하지 않습니다.

AI 점검은 Codex의 별도 매일 08:00 작업으로 설정합니다. GitHub Actions 실행 여부와 시세 파일의 날짜·상태·수익률을 확인하고, 필요하면 수동 실행으로 복구합니다. Codex의 점검 작업은 앱 실행 환경에 의존하지만 기본 가격 갱신은 GitHub에서 독립적으로 수행합니다.

조회 실패 종목은 이전 종가·가격 기준일을 유지하고 `stale`로 표시합니다. 전 종목 조회 실패 시 기존 파일을 덮어쓰지 않고 워크플로를 실패 처리합니다. 가격 제공처: Yahoo Finance (지연 가능).

## GitHub Pages 설정

저장소 **Settings → Pages → Build and deployment → Source: GitHub Actions**를 사용합니다. 워크플로는 정적 HTML/JS/CSS와 두 JSON만 배포하며, 원본 발표 PDF/PPT는 업로드하지 않습니다. 별도 서버나 API 키가 필요 없습니다.

## 로컬 사용

`start.command`를 더블클릭하거나 다음을 실행합니다 (Python 3.9 이상, 외부 패키지 불필요).

```sh
python3 server.py
```

http://127.0.0.1:8765 에 접속합니다. 화면 새로고침 버튼은 저장된 JSON을 다시 읽습니다. 가격 수집은 아래 명령으로 별도 실행합니다.

```sh
python3 server.py --refresh
python3 server.py --refresh --as-of 2026-11-12
python3 -m unittest discover -s tests -v
```

브라우저의 5분 갱신은 배포된 JSON을 다시 읽는 기능입니다. 새로운 주가 수집은 일일 워크플로가 수행합니다.
