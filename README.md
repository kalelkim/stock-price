# stock-price — 국내외 주식·ETF 가격 수집기

국내(KRX)·해외(미국 등) 주식·ETF의 최신 종가를 [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)로 조회해
날짜별 JSON으로 누적 저장한다. GitHub Actions가 평일 08:00 KST에 자동 실행하여 결과를 commit/push 한다.

## 구조

- `tickers.json` — 조회할 종목 목록(직접 편집)
- `stock_price/` — 수집 프로그램(watchlist / fetcher / formatter / storage / main)
- `data/YYYY-MM-DD.json` — 실행마다 쌓이는 가격 기록
- `.github/workflows/fetch-prices.yml` — 자동 실행 워크플로

## 로컬 실행

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1   |   bash: source .venv/Scripts/activate
pip install -r requirements.txt
python -m stock_price.main      # data/<오늘 KST 날짜>.json 생성
pytest                          # 테스트
```

## 종목 추가/삭제

`tickers.json`의 `tickers` 배열을 편집한다. 코드 수정은 필요 없다.

```json
{ "symbol": "005930", "name": "삼성전자" }
```

- 심볼만 보고 시장·통화를 자동 추론한다: 6자리 숫자 → KRX·KRW, 영문 → US·USD.
- 다른 시장은 `"currency"`, `"market"`을 직접 지정해 덮어쓸 수 있다.

## 출력 형식

```json
{
  "run_date": "2026-05-31",
  "fetched_at": "2026-05-30T23:00:12Z",
  "count": 1,
  "prices": [
    { "symbol": "005930", "name": "삼성전자", "market": "KRX", "currency": "KRW",
      "price_date": "2026-05-29", "close": 73500.0, "previous_close": 74000.0,
      "change": -500.0, "change_pct": -0.68, "volume": 12345678 }
  ],
  "errors": []
}
```

- `run_date`(실행일, KST)와 `price_date`(종가의 거래일)는 다르다. 08:00 KST는 KRX 개장 전이라
  국내·해외 모두 직전 거래일 종가가 기록된다.
- 조회 실패 종목은 `errors`에 기록되고 나머지는 정상 저장된다(부분 실패 허용).

## GitHub Actions 초기 설정 (1회)

1. GitHub에 저장소를 만들고 push: `git remote add origin <URL> && git push -u origin main`
2. **Settings → Actions → General → Workflow permissions**에서 **"Read and write permissions"**를 켠다
   (꺼져 있으면 워크플로가 push 하지 못한다).
3. 이후 평일 08:00 KST에 자동 실행되며, Actions 탭의 **Run workflow** 버튼으로 수동 실행도 가능하다.
