# 국내외 주식·ETF 가격 수집기 — 설계 문서

- **작성일**: 2026-05-31
- **상태**: 승인됨 (구현 대기)
- **요약**: 국내외 주식·ETF의 최신 가격을 FinanceDataReader로 조회해 날짜별 JSON으로 저장하고, GitHub Actions가 평일 1회 자동 실행하여 git commit/push 한다.

---

## 1. 목표 (Goal)

국내(KRX) 및 해외(미국 등) 주식·ETF의 최신 가격을 주기적으로 수집해 **시계열 히스토리**로 누적 저장한다. 저장은 git 저장소에 날짜별 JSON 파일로 쌓이며, 수집·저장·커밋·푸시는 GitHub Actions가 자동으로 수행한다.

## 2. 결정 사항 요약 (Decisions)

브레인스토밍에서 확정한 선택지:

| 항목 | 결정 | 비고 |
|------|------|------|
| 저장 목적 | **시계열 히스토리 누적** | 실행마다 기록을 쌓음 |
| 데이터 출처 | **FinanceDataReader** | 무료·API키 불필요·국내외 커버 |
| 종목 관리 | **JSON 설정 파일**(`tickers.json`) | 코드 수정 없이 편집 |
| 실행 주기 | **평일 1회, 18:30 KST** | cron `30 9 * * 1-5` (UTC) |
| 파일 구조 | **날짜별 파일**(`data/YYYY-MM-DD.json`) | 실행마다 새 파일 1개 |
| 프로그램 구조 | **모듈 분리 + 견고한 수집** | 순수 로직과 네트워크 분리 |
| 출력 필드 | 기본 스키마 그대로(§6) | `volume` 포함 |
| 휴일 동작 | 직전 종가를 그대로 기록 | 휴일 스킵 로직은 향후 과제 |

## 3. 아키텍처 & 데이터 흐름

```
GitHub Actions (평일 18:30 KST = cron "30 9 * * 1-5", UTC 기준)
        │
        ▼
[main] 조율
   1) watchlist  →  tickers.json 읽고 검증 → 종목 리스트
   2) fetcher    →  종목별로 FinanceDataReader 조회 (실패 시 재시도 → 건너뜀)
   3) formatter  →  최신 종가·전일종가·등락률·통화·시장·거래일 계산하여 레코드 생성
   4) storage    →  data/YYYY-MM-DD.json 으로 원자적 저장 (KST 날짜 기준)
        │
        ▼
git add data/ → (변경 있을 때만) commit & push  ← 기본 GITHUB_TOKEN 사용, PAT 불필요
```

**핵심 원칙**: 네트워크에 의존하는 부분(`fetcher`)과 순수 로직(`formatter`, `storage`)을 분리한다. `fetcher`는 FinanceDataReader를 직접 호출하지 않고 "조회 함수(reader)"를 **주입**받으므로, 테스트 시 가짜 데이터를 반환하는 reader로 대체해 네트워크 없이 검증할 수 있다.

## 4. 모듈(컴포넌트) 책임

각 모듈은 단일 책임을 가지며 잘 정의된 인터페이스로 통신한다. 아래 시그니처는 구현 시 가이드이며 TDD 과정에서 확정한다.

### `watchlist.py` — 설정 로드/검증
- `load_watchlist(path) -> list[Ticker]`
- `Ticker` = 데이터클래스: `symbol`, `name`, `currency`(선택), `market`(선택)
- 검증: 빈 심볼 거부, 심볼 중복 거부, `tickers` 키 누락/형식 오류 시 명확한 예외.
- 의존성: 파일시스템.

### `fetcher.py` — FDR 조회 + 재시도
- `fetch_latest(symbol, reader, retries=3, lookback_days=10) -> pandas.DataFrame`
  - 최근 `lookback_days` 일 구간을 조회해 최신 2거래일을 확보(등락률 계산용).
  - `retries`회까지 재시도하며, 비어 있거나 예외면 마지막에 `FetchError`를 던진다.
- `default_reader(symbol, start) -> DataFrame` — `fdr.DataReader`를 감싼 기본 reader.
- 의존성: FinanceDataReader (단, `fetch_latest`는 reader 주입을 받아 테스트 가능).

### `formatter.py` — 레코드 생성 (순수)
- `build_record(ticker, df) -> dict` — `Ticker` 메타 + 조회 DataFrame에서 가격 레코드 생성.
- `infer_market_currency(symbol) -> (market, currency)` — §7 규칙 적용.
- 데이터가 1행뿐이면 `previous_close`/`change`/`change_pct`는 `null`.
- 의존성: 없음(순수 함수) → 네트워크 없이 단위 테스트.

### `storage.py` — 경로 결정 + 원자적 쓰기
- `day_file_path(run_date, data_dir) -> Path` — `data/YYYY-MM-DD.json`.
- `build_payload(run_date, fetched_at, records, errors) -> dict` — §6 출력 스키마 생성.
- `write_day_file(path, payload) -> None` — 임시파일에 쓰고 rename 하는 원자적 쓰기, JSON은 UTF-8·`ensure_ascii=False`·들여쓰기 2.
- 의존성: 파일시스템.

### `main.py` — 조율
- 절차: watchlist 로드 → 종목별 `fetch_latest`+`build_record`(성공은 records, 실패는 errors 수집) → `build_payload` → `write_day_file`.
- 시각(`run_date`, `fetched_at`)은 **Asia/Seoul** 기준으로 계산하되, 테스트를 위해 "현재 시각"을 주입 가능한 형태로 둔다.
- **모든** 종목이 실패하면 종료코드 1을 반환(Actions 실패 표시 → 알림). 일부 성공이면 0.
- 실행: `python -m stock_price.main`.

## 5. 입력 — `tickers.json`

사람이 직접 편집하는 워치리스트.

```json
{
  "tickers": [
    { "symbol": "005930", "name": "삼성전자" },
    { "symbol": "069500", "name": "KODEX 200" },
    { "symbol": "AAPL",   "name": "Apple" },
    { "symbol": "SPY",    "name": "SPDR S&P 500 ETF" }
  ]
}
```

- `currency`/`market`은 선택 필드. 지정하지 않으면 심볼로 자동 추론(§7). 지정하면 추론을 덮어쓴다.

## 6. 출력 — `data/2026-05-31.json`

실행마다 1개 파일. KST 기준 날짜로 파일명을 정한다.

```json
{
  "run_date": "2026-05-31",
  "fetched_at": "2026-05-31T09:30:12Z",
  "count": 4,
  "prices": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "market": "KRX",
      "currency": "KRW",
      "price_date": "2026-05-29",
      "close": 73500.0,
      "previous_close": 74000.0,
      "change": -500.0,
      "change_pct": -0.68,
      "volume": 12345678
    }
  ],
  "errors": [
    { "symbol": "XYZ", "message": "no data returned" }
  ]
}
```

- `run_date`(실행 날짜, KST)와 `price_date`(실제 종가의 거래일)를 **구분**한다.
- 미국 종목을 KST 저녁에 조회하면 `price_date`는 직전 미국 거래일이 된다(정상).
- `change_pct`는 백분율(단위 %), 소수 둘째 자리 반올림.
- 조회 실패 종목은 `prices`에서 제외하고 `errors`에 사유와 함께 기록한다.

## 7. 통화·시장 추론 규칙

- **6자리 숫자 심볼** → `market: "KRX"`, `currency: "KRW"`.
- **영문 심볼** → `market: "US"`, `currency: "USD"`.
- `tickers.json`에서 `currency`/`market`을 명시하면 추론을 덮어쓴다(향후 다른 시장 확장 여지).

## 8. 에러 처리 & 견고성

- **부분 실패 허용**: 한 종목 실패(재시도 후에도) → 건너뛰고 `errors`에 기록, 나머지는 정상 저장.
- **전체 실패 시에만 빨간불**: 모든 종목 실패 시 종료코드 1 → Actions 실패 → 메일 알림.
- **같은 날 재실행 멱등성**: 그날 파일을 덮어쓰고, 내용이 바뀌었을 때만 커밋(빈 커밋 방지).
- **휴일 동작**: 평일이라도 KRX 휴장일엔 FDR이 직전 종가를 반환 → 그날 파일에 "그 시점 기준 최신가"가 기록된다.

## 9. 테스트 전략 (pytest, TDD)

- `formatter`: 등락률 계산, 통화/시장 추론, 1행만 있을 때(전일종가 없음) 처리 → 네트워크 없음.
- `storage`: 날짜→경로 변환, JSON 구조, 원자적 쓰기, 같은 날 덮어쓰기 → 임시 디렉터리.
- `watchlist`: 정상/누락/중복/형식오류 설정 파싱.
- `fetcher`: 가짜 reader 주입으로 재시도·부분실패·빈 데이터 처리 검증(실제 네트워크 호출 없음).
- `main`: 가짜 fetcher/storage로 조율·종료코드(부분 성공=0, 전체 실패=1) 검증.

## 10. GitHub Actions 워크플로 (`.github/workflows/fetch-prices.yml`)

- **트리거**: `schedule: cron "30 9 * * 1-5"`(평일 18:30 KST) + `workflow_dispatch`(수동 버튼).
- **권한**: `permissions: contents: write` (기본 `GITHUB_TOKEN`으로 push — 별도 PAT·Secret 불필요).
- **단계**: checkout → setup-python → `pip install -r requirements.txt` → `python -m stock_price.main` → 변경 있으면 봇 계정(`github-actions[bot]`)으로 commit & push.
- **참고**: GitHub cron은 부하 시 수 분 지연될 수 있으나 일별 종가엔 무방. 한국은 서머타임이 없어 시각 보정 불필요.

워크플로 스케치:

```yaml
name: fetch-prices
on:
  schedule:
    - cron: "30 9 * * 1-5"   # 18:30 KST (UTC+9)
  workflow_dispatch: {}
permissions:
  contents: write
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m stock_price.main
      - name: Commit & push if changed
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git diff --staged --quiet || git commit -m "data: prices $(date -u +%Y-%m-%d)"
          git push
```

### 10.1 초기 설정 (1회)

워크플로가 자동 push 하려면 한 번만 해두면 되는 설정:

1. GitHub에 저장소를 만들고 이 코드를 push 한다(`git remote add origin … && git push -u origin main`).
2. **Settings → Actions → General → Workflow permissions**에서 **"Read and write permissions"**가 켜져 있어야 한다. (일부 저장소는 기본이 읽기 전용이라 이게 꺼져 있으면 워크플로의 `contents: write`만으로는 push가 거부될 수 있다.)
3. 이후 평일 18:30 KST마다 자동 실행되며, GitHub Actions 화면에서 **Run workflow** 버튼으로 수동 실행도 가능하다.

## 11. 프로젝트 구조 & 산출물

```
stock-price/
├── .github/workflows/fetch-prices.yml
├── stock_price/
│   ├── __init__.py
│   ├── watchlist.py
│   ├── fetcher.py
│   ├── formatter.py
│   ├── storage.py
│   └── main.py
├── tests/
│   ├── test_watchlist.py
│   ├── test_fetcher.py
│   ├── test_formatter.py
│   ├── test_storage.py
│   └── test_main.py
├── data/.gitkeep          # 날짜별 JSON이 여기에 쌓임
├── tickers.json           # 조회할 종목 목록
├── requirements.txt       # FinanceDataReader, pandas, pytest
├── README.md              # 사용법·종목 추가법
└── .gitignore
```

실행/테스트(로컬·CI 공통): `python -m stock_price.main`, `pytest`.

## 12. 의존성

- 런타임: `FinanceDataReader`, `pandas`(FDR 의존).
- 개발/테스트: `pytest`.
- Python 3.12 기준.

## 13. 범위 밖 (YAGNI)

- 실시간/장중 시세, 분 단위 수집.
- 환율 변환(해외 종목을 KRW로 환산) — 네이티브 통화 그대로 저장.
- 차트·대시보드·웹 UI.
- 한국 공휴일 자동 스킵(필요 시 향후 추가).
- `latest.json` 스냅샷(히스토리만 저장하기로 결정).

## 14. 향후 확장 여지

- 한국 공휴일 캘린더로 휴장일 스킵.
- 월별 폴더(`data/2026-05/`)로 파일 정리.
- 간단한 분석/차트 노트북 또는 정적 페이지.
- 다른 시장(도쿄·홍콩 등) 심볼 추론 규칙 추가.
