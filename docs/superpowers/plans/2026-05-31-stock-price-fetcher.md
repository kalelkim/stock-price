# 국내외 주식·ETF 가격 수집기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FinanceDataReader로 국내외 주식·ETF의 최신 종가를 조회해 날짜별 JSON으로 누적 저장하고, GitHub Actions가 평일 08:00 KST에 자동 실행하여 commit/push 한다.

**Architecture:** 네트워크 의존 코드(`fetcher`)와 순수 로직(`formatter`, `storage`)을 분리한다. `fetcher`는 "조회 함수(reader)"를 주입받아 테스트 시 가짜 데이터로 대체된다. `main`이 watchlist 로드 → 종목별 조회/포맷(부분 실패 허용) → 날짜별 파일 저장을 조율하고 종료코드를 반환한다.

**Tech Stack:** Python 3.12, FinanceDataReader, pandas, pytest, GitHub Actions.

---

## 실행 환경 참고 (executor notes)

- OS: Windows. 셸은 PowerShell이 기본이나, 아래 명령은 모두 크로스플랫폼(`python`, `pytest`, `git`)이다.
- 가상환경 권장: `python -m venv .venv` 후 PowerShell `.\.venv\Scripts\Activate.ps1` (bash는 `source .venv/Scripts/activate`).
- **모든 git 커밋 메시지는 다음 트레일러로 끝낸다**(각 커밋 명령에 두 번째 `-m`으로 포함):
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- 단위 테스트는 네트워크가 필요 없다(가짜 reader 주입). 네트워크는 Task 8의 통합 실행에서만 사용한다.
- 저장소는 이미 `git init` 되어 있고 `main` 브랜치에 설계 문서가 커밋돼 있다.

## File Structure (생성/수정 파일)

| 파일 | 책임 |
|------|------|
| `pyproject.toml` | pytest 설정(`pythonpath`, `testpaths`) |
| `requirements.txt` | 런타임·테스트 의존성 |
| `.gitignore` | 파이썬 아티팩트 무시(`data/`는 무시하지 않음) |
| `tickers.json` | 조회할 종목 목록(사람이 편집) |
| `data/.gitkeep` | 빈 `data/` 디렉터리를 저장소에 유지 |
| `stock_price/__init__.py` | 패키지 마커 |
| `stock_price/watchlist.py` | `tickers.json` 로드/검증, `Ticker` 정의 |
| `stock_price/formatter.py` | 순수 로직: 시장/통화 추론, 가격 레코드 생성 |
| `stock_price/storage.py` | 날짜별 경로 결정, payload 구성, 원자적 쓰기 |
| `stock_price/fetcher.py` | FDR 조회 + 재시도(reader 주입) |
| `stock_price/main.py` | 조율 + 종료코드 + `__main__` 진입점 |
| `tests/test_watchlist.py` | watchlist 테스트 |
| `tests/test_formatter.py` | formatter 테스트 |
| `tests/test_storage.py` | storage 테스트 |
| `tests/test_fetcher.py` | fetcher 테스트 |
| `tests/test_main.py` | main 조율 테스트 |
| `.github/workflows/fetch-prices.yml` | 스케줄·수동 실행, commit/push |
| `README.md` | 사용법·종목 추가법·초기 설정 |

각 모듈은 단일 책임을 가진다. 모듈 간 의존: `formatter`와 `main`이 `watchlist.Ticker`를 import 하므로 **watchlist를 가장 먼저 구현**한다.

---

## Task 1: 프로젝트 스캐폴딩 & 의존성

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `tickers.json`
- Create: `data/.gitkeep`
- Create: `stock_price/__init__.py`

- [ ] **Step 1: requirements.txt 작성**

`requirements.txt`:
```
# 런타임
FinanceDataReader
pandas
# 개발/테스트
pytest
```

- [ ] **Step 2: pyproject.toml 작성 (pytest가 패키지를 찾고 tests/를 수집하도록)**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: .gitignore 작성 (data/ 는 무시하지 않는다 — 커밋 대상)**

`.gitignore`:
```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
*.egg-info/
.idea/
.vscode/
```

- [ ] **Step 4: tickers.json 작성 (샘플 종목)**

`tickers.json`:
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

- [ ] **Step 5: 패키지 파일 생성**

`stock_price/__init__.py`:
```python
"""국내외 주식·ETF 가격 수집기."""
```

`data/.gitkeep`: (빈 파일)
```
```

- [ ] **Step 6: 의존성 설치 및 임포트 확인**

Run:
```
pip install -r requirements.txt
python -c "import stock_price; print('ok')"
```
Expected: 설치 성공 후 `ok` 출력. (FinanceDataReader 설치 시 pandas 등 함께 설치됨)

- [ ] **Step 7: 커밋**

```bash
git add requirements.txt pyproject.toml .gitignore tickers.json data/.gitkeep stock_price/__init__.py
git commit -m "chore: scaffold project structure and dependencies" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: watchlist (Ticker + load_watchlist)

**Files:**
- Create: `tests/test_watchlist.py`
- Create: `stock_price/watchlist.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_watchlist.py`:
```python
import json
from pathlib import Path

import pytest

from stock_price.watchlist import Ticker, WatchlistError, load_watchlist


def _write(tmp_path: Path, data) -> Path:
    p = tmp_path / "tickers.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_loads_valid_tickers(tmp_path):
    p = _write(tmp_path, {"tickers": [
        {"symbol": "005930", "name": "삼성전자"},
        {"symbol": "AAPL", "name": "Apple"},
    ]})
    assert load_watchlist(p) == [
        Ticker(symbol="005930", name="삼성전자"),
        Ticker(symbol="AAPL", name="Apple"),
    ]


def test_name_defaults_to_symbol(tmp_path):
    p = _write(tmp_path, {"tickers": [{"symbol": "SPY"}]})
    assert load_watchlist(p)[0].name == "SPY"


def test_currency_and_market_overrides(tmp_path):
    p = _write(tmp_path, {"tickers": [
        {"symbol": "7203", "name": "Toyota", "currency": "JPY", "market": "TSE"},
    ]})
    t = load_watchlist(p)[0]
    assert t.currency == "JPY"
    assert t.market == "TSE"


def test_missing_tickers_key_raises(tmp_path):
    p = _write(tmp_path, {"foo": []})
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_empty_tickers_list_raises(tmp_path):
    p = _write(tmp_path, {"tickers": []})
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_blank_symbol_raises(tmp_path):
    p = _write(tmp_path, {"tickers": [{"symbol": "  ", "name": "x"}]})
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_duplicate_symbol_raises(tmp_path):
    p = _write(tmp_path, {"tickers": [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "AAPL", "name": "Apple Inc"},
    ]})
    with pytest.raises(WatchlistError):
        load_watchlist(p)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_watchlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stock_price.watchlist'`

- [ ] **Step 3: 최소 구현 작성**

`stock_price/watchlist.py`:
```python
"""워치리스트(tickers.json) 로드 및 검증."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class WatchlistError(Exception):
    """tickers.json 형식/내용 오류."""


@dataclass(frozen=True)
class Ticker:
    symbol: str
    name: str
    currency: str | None = None
    market: str | None = None


def load_watchlist(path: str | Path) -> list[Ticker]:
    """tickers.json을 읽어 Ticker 리스트로 반환. 형식 오류 시 WatchlistError."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or "tickers" not in raw:
        raise WatchlistError("최상위에 'tickers' 키가 없습니다.")
    items = raw["tickers"]
    if not isinstance(items, list) or not items:
        raise WatchlistError("'tickers'는 비어 있지 않은 리스트여야 합니다.")

    tickers: list[Ticker] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise WatchlistError(f"tickers[{i}]는 객체여야 합니다.")
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise WatchlistError(f"tickers[{i}]의 'symbol'이 비어 있습니다.")
        symbol = symbol.strip()
        if symbol in seen:
            raise WatchlistError(f"심볼 중복: {symbol}")
        seen.add(symbol)
        name = item.get("name") or symbol
        tickers.append(Ticker(
            symbol=symbol,
            name=str(name),
            currency=item.get("currency"),
            market=item.get("market"),
        ))
    return tickers
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_watchlist.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_watchlist.py stock_price/watchlist.py
git commit -m "feat: load and validate ticker watchlist from JSON" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: formatter (시장/통화 추론 + 레코드 생성)

**Files:**
- Create: `tests/test_formatter.py`
- Create: `stock_price/formatter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_formatter.py`:
```python
import pandas as pd

from stock_price.formatter import build_record, infer_market_currency
from stock_price.watchlist import Ticker


def _df(closes, volumes=None, dates=None):
    n = len(closes)
    if dates is None:
        dates = pd.date_range("2026-05-25", periods=n, freq="D")
    data = {"Close": closes}
    if volumes is not None:
        data["Volume"] = volumes
    return pd.DataFrame(data, index=pd.DatetimeIndex(dates))


def test_korean_six_digit_is_krx_krw():
    assert infer_market_currency("005930") == ("KRX", "KRW")


def test_etf_six_digit_is_krx_krw():
    assert infer_market_currency("069500") == ("KRX", "KRW")


def test_alpha_symbol_is_us_usd():
    assert infer_market_currency("AAPL") == ("US", "USD")


def test_build_record_basic():
    t = Ticker(symbol="005930", name="삼성전자")
    df = _df([74000.0, 73500.0], volumes=[111, 12345678],
             dates=["2026-05-28", "2026-05-29"])
    assert build_record(t, df) == {
        "symbol": "005930",
        "name": "삼성전자",
        "market": "KRX",
        "currency": "KRW",
        "price_date": "2026-05-29",
        "close": 73500.0,
        "previous_close": 74000.0,
        "change": -500.0,
        "change_pct": -0.68,
        "volume": 12345678,
    }


def test_build_record_single_row_has_null_changes():
    t = Ticker(symbol="AAPL", name="Apple")
    df = _df([200.0], volumes=[5000], dates=["2026-05-29"])
    rec = build_record(t, df)
    assert rec["previous_close"] is None
    assert rec["change"] is None
    assert rec["change_pct"] is None
    assert rec["close"] == 200.0
    assert rec["market"] == "US"
    assert rec["currency"] == "USD"


def test_build_record_without_volume_column():
    t = Ticker(symbol="AAPL", name="Apple")
    df = _df([100.0, 110.0])
    rec = build_record(t, df)
    assert rec["volume"] is None
    assert rec["change"] == 10.0
    assert rec["change_pct"] == 10.0


def test_build_record_respects_overrides():
    t = Ticker(symbol="AAPL", name="Apple", currency="EUR", market="XETRA")
    rec = build_record(t, _df([100.0, 110.0]))
    assert rec["currency"] == "EUR"
    assert rec["market"] == "XETRA"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_formatter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stock_price.formatter'`

- [ ] **Step 3: 최소 구현 작성**

`stock_price/formatter.py`:
```python
"""가격 레코드 생성 — 순수 로직(네트워크/파일 의존 없음)."""
from __future__ import annotations

import pandas as pd

from stock_price.watchlist import Ticker


def infer_market_currency(symbol: str) -> tuple[str, str]:
    """심볼로 시장·통화 추론. 6자리 숫자 → KRX/KRW, 그 외 → US/USD."""
    if symbol.isdigit() and len(symbol) == 6:
        return ("KRX", "KRW")
    return ("US", "USD")


def build_record(ticker: Ticker, df: pd.DataFrame) -> dict:
    """조회된 DataFrame에서 가격 레코드(dict)를 만든다.

    df는 DatetimeIndex와 'Close' 컬럼을 가진다고 가정한다.
    'Volume' 컬럼은 선택. 행이 1개뿐이면 등락 관련 값은 None.
    """
    inferred_market, inferred_currency = infer_market_currency(ticker.symbol)
    market = ticker.market or inferred_market
    currency = ticker.currency or inferred_currency

    close = float(df["Close"].iloc[-1])
    price_date = pd.Timestamp(df.index[-1]).date().isoformat()

    volume = None
    if "Volume" in df.columns:
        v = df["Volume"].iloc[-1]
        if pd.notna(v):
            volume = int(v)

    if len(df) >= 2:
        previous_close = float(df["Close"].iloc[-2])
        change = round(close - previous_close, 4)
        change_pct = round((close - previous_close) / previous_close * 100, 2)
    else:
        previous_close = None
        change = None
        change_pct = None

    return {
        "symbol": ticker.symbol,
        "name": ticker.name,
        "market": market,
        "currency": currency,
        "price_date": price_date,
        "close": close,
        "previous_close": previous_close,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_formatter.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_formatter.py stock_price/formatter.py
git commit -m "feat: build price records with market/currency inference" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: storage (경로 + payload + 원자적 쓰기)

**Files:**
- Create: `tests/test_storage.py`
- Create: `stock_price/storage.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_storage.py`:
```python
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from stock_price.storage import build_payload, day_file_path, write_day_file

KST = timezone(timedelta(hours=9))


def test_day_file_path():
    assert day_file_path(date(2026, 5, 31), Path("data")) == Path("data") / "2026-05-31.json"


def test_build_payload_shape_and_utc_conversion():
    payload = build_payload(
        run_date=date(2026, 5, 31),
        fetched_at=datetime(2026, 5, 31, 8, 0, 0, tzinfo=KST),
        records=[{"symbol": "AAPL"}],
        errors=[{"symbol": "XYZ", "message": "no data"}],
    )
    assert payload["run_date"] == "2026-05-31"
    assert payload["fetched_at"] == "2026-05-30T23:00:00Z"
    assert payload["count"] == 1
    assert payload["prices"] == [{"symbol": "AAPL"}]
    assert payload["errors"] == [{"symbol": "XYZ", "message": "no data"}]


def test_write_day_file_atomic_and_utf8(tmp_path):
    path = tmp_path / "data" / "2026-05-31.json"
    payload = {"run_date": "2026-05-31", "prices": [{"name": "삼성전자"}]}
    write_day_file(path, payload)

    assert path.exists()
    assert not (tmp_path / "data" / "2026-05-31.json.tmp").exists()
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "삼성전자" in text          # ensure_ascii=False 확인
    assert json.loads(text) == payload


def test_write_day_file_overwrites_same_day(tmp_path):
    path = tmp_path / "data" / "2026-05-31.json"
    write_day_file(path, {"count": 1})
    write_day_file(path, {"count": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"count": 2}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stock_price.storage'`

- [ ] **Step 3: 최소 구현 작성**

`stock_price/storage.py`:
```python
"""날짜별 JSON 파일 저장 — 경로 결정, payload 구성, 원자적 쓰기."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path


def day_file_path(run_date: date, data_dir: str | Path) -> Path:
    """data_dir/YYYY-MM-DD.json 경로."""
    return Path(data_dir) / f"{run_date.isoformat()}.json"


def build_payload(
    run_date: date,
    fetched_at: datetime,
    records: list[dict],
    errors: list[dict],
) -> dict:
    """출력 JSON payload 구성. fetched_at은 UTC 'Z' 형식으로 기록."""
    return {
        "run_date": run_date.isoformat(),
        "fetched_at": fetched_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(records),
        "prices": records,
        "errors": errors,
    }


def write_day_file(path: str | Path, payload: dict) -> None:
    """payload를 JSON으로 원자적으로 쓴다(임시파일 → rename). UTF-8, 한글 보존."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_storage.py stock_price/storage.py
git commit -m "feat: store daily price payload as atomic JSON file" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: fetcher (FDR 조회 + 재시도)

**Files:**
- Create: `tests/test_fetcher.py`
- Create: `stock_price/fetcher.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_fetcher.py`:
```python
import pandas as pd
import pytest

from stock_price.fetcher import FetchError, fetch_latest


def _df():
    return pd.DataFrame({"Close": [1.0, 2.0]},
                        index=pd.date_range("2026-05-28", periods=2))


class Reader:
    """fail_times번 실패(빈 DataFrame 또는 예외) 후 df 반환하는 가짜 reader."""

    def __init__(self, fail_times, df=None, raises=False):
        self.calls = 0
        self.fail_times = fail_times
        self.df = df
        self.raises = raises

    def __call__(self, symbol):
        self.calls += 1
        if self.calls <= self.fail_times:
            if self.raises:
                raise RuntimeError("boom")
            return pd.DataFrame()  # 빈 결과
        return self.df


def test_returns_on_first_success():
    df = _df()
    reader = Reader(fail_times=0, df=df)
    sleeps = []
    out = fetch_latest("AAA", reader, sleep=lambda s: sleeps.append(s))
    assert out is df
    assert reader.calls == 1
    assert sleeps == []


def test_retries_then_succeeds():
    df = _df()
    reader = Reader(fail_times=2, df=df, raises=True)
    sleeps = []
    out = fetch_latest("AAA", reader, retries=3, sleep=lambda s: sleeps.append(s))
    assert out is df
    assert reader.calls == 3
    assert len(sleeps) == 2


def test_empty_always_raises_fetcherror():
    reader = Reader(fail_times=99)  # 항상 빈 결과
    sleeps = []
    with pytest.raises(FetchError):
        fetch_latest("AAA", reader, retries=3, sleep=lambda s: sleeps.append(s))
    assert reader.calls == 3
    assert len(sleeps) == 2


def test_exception_always_raises_fetcherror_with_symbol():
    reader = Reader(fail_times=99, raises=True)
    with pytest.raises(FetchError) as exc:
        fetch_latest("ZZZ", reader, retries=2, sleep=lambda s: None)
    assert "ZZZ" in str(exc.value)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stock_price.fetcher'`

- [ ] **Step 3: 최소 구현 작성**

`stock_price/fetcher.py`:
```python
"""FinanceDataReader 조회 + 재시도. reader 주입으로 테스트 가능."""
from __future__ import annotations

import time
from typing import Callable

import pandas as pd


class FetchError(Exception):
    """재시도 후에도 데이터를 얻지 못함."""


def fetch_latest(
    symbol: str,
    reader: Callable[[str], pd.DataFrame],
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
    backoff_seconds: float = 1.0,
) -> pd.DataFrame:
    """reader(symbol)로 데이터를 가져온다.

    비었거나 예외면 재시도하고, 끝까지 실패하면 FetchError를 던진다.
    """
    last_err: Exception | None = None
    for attempt in range(retries):
        df = None
        try:
            df = reader(symbol)
        except Exception as e:  # noqa: BLE001 - 어떤 조회 실패든 재시도 대상
            last_err = e
        if df is not None and not df.empty:
            return df
        if attempt < retries - 1:
            sleep(backoff_seconds)
    suffix = f" ({last_err})" if last_err else ""
    raise FetchError(f"{symbol}: {retries}회 시도 후 데이터 없음{suffix}")


def default_reader(start: str) -> Callable[[str], pd.DataFrame]:
    """FinanceDataReader 기반 기본 reader 생성(지연 import).

    start 이후 구간을 조회한다(최신 2거래일 확보용으로 넉넉히).
    """
    import FinanceDataReader as fdr

    def reader(symbol: str) -> pd.DataFrame:
        return fdr.DataReader(symbol, start)

    return reader
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_fetcher.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_fetcher.py stock_price/fetcher.py
git commit -m "feat: fetch latest prices with retry and injectable reader" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: main (조율 + 종료코드 + 진입점)

**Files:**
- Create: `tests/test_main.py`
- Create: `stock_price/main.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_main.py`:
```python
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from stock_price.main import run

KST = timezone(timedelta(hours=9))


def _write_watchlist(tmp_path, symbols):
    p = tmp_path / "tickers.json"
    p.write_text(
        json.dumps({"tickers": [{"symbol": s, "name": s} for s in symbols]}),
        encoding="utf-8",
    )
    return p


def _good_df():
    return pd.DataFrame(
        {"Close": [100.0, 110.0], "Volume": [10, 20]},
        index=pd.date_range("2026-05-28", periods=2),
    )


def _make_reader(good):
    def reader(symbol):
        if symbol in good:
            return _good_df()
        raise RuntimeError("no data")
    return reader


def test_partial_success_writes_file_and_returns_zero(tmp_path):
    wl = _write_watchlist(tmp_path, ["AAA", "BBB"])
    data_dir = tmp_path / "data"
    code = run(
        watchlist_path=wl,
        data_dir=data_dir,
        now=datetime(2026, 5, 31, 8, 0, tzinfo=KST),
        reader=_make_reader({"AAA"}),
        sleep=lambda s: None,
    )
    assert code == 0
    out = data_dir / "2026-05-31.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["run_date"] == "2026-05-31"
    assert payload["fetched_at"] == "2026-05-30T23:00:00Z"
    assert payload["count"] == 1
    assert [p["symbol"] for p in payload["prices"]] == ["AAA"]
    assert [e["symbol"] for e in payload["errors"]] == ["BBB"]


def test_all_fail_returns_one(tmp_path):
    wl = _write_watchlist(tmp_path, ["AAA", "BBB"])
    data_dir = tmp_path / "data"
    code = run(
        watchlist_path=wl,
        data_dir=data_dir,
        now=datetime(2026, 5, 31, 8, 0, tzinfo=KST),
        reader=_make_reader(set()),
        sleep=lambda s: None,
    )
    assert code == 1
    payload = json.loads((data_dir / "2026-05-31.json").read_text(encoding="utf-8"))
    assert payload["count"] == 0
    assert len(payload["errors"]) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stock_price.main'`

- [ ] **Step 3: 최소 구현 작성**

`stock_price/main.py`:
```python
"""조율: 워치리스트 로드 → 종목별 조회/포맷 → 날짜별 파일 저장. 종료코드 반환."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from stock_price.fetcher import default_reader, fetch_latest
from stock_price.formatter import build_record
from stock_price.storage import build_payload, day_file_path, write_day_file
from stock_price.watchlist import load_watchlist

KST = timezone(timedelta(hours=9))
LOOKBACK_DAYS = 10


def run(
    watchlist_path: str | Path,
    data_dir: str | Path,
    now: Optional[datetime] = None,
    reader: Optional[Callable[[str], pd.DataFrame]] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """가격 수집 1회 실행.

    일부라도 성공하면 0, 모든 종목이 실패하면 1을 반환한다.
    now(tz-aware)와 reader는 테스트에서 주입한다.
    """
    now = now or datetime.now(KST)
    run_date = now.date()

    if reader is None:
        start = (run_date - timedelta(days=LOOKBACK_DAYS)).isoformat()
        reader = default_reader(start)

    tickers = load_watchlist(watchlist_path)

    records: list[dict] = []
    errors: list[dict] = []
    for ticker in tickers:
        try:
            df = fetch_latest(ticker.symbol, reader, sleep=sleep)
            records.append(build_record(ticker, df))
        except Exception as e:  # noqa: BLE001 - 종목별 실패는 기록 후 계속
            errors.append({"symbol": ticker.symbol, "message": str(e)})

    payload = build_payload(run_date, now, records, errors)
    write_day_file(day_file_path(run_date, data_dir), payload)

    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(run(watchlist_path=Path("tickers.json"), data_dir=Path("data")))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `pytest -v`
Expected: PASS (24 passed) — watchlist 7 + formatter 7 + storage 4 + fetcher 4 + main 2

- [ ] **Step 6: 커밋**

```bash
git add tests/test_main.py stock_price/main.py
git commit -m "feat: orchestrate fetch run with partial-failure handling and exit code" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: GitHub Actions 워크플로

**Files:**
- Create: `.github/workflows/fetch-prices.yml`

- [ ] **Step 1: 워크플로 파일 작성**

`.github/workflows/fetch-prices.yml`:
```yaml
name: fetch-prices

on:
  schedule:
    - cron: "0 23 * * 0-4"   # 08:00 KST (UTC 전일 23:00; KST 월~금 = UTC 일~목)
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Fetch prices
        run: python -m stock_price.main

      - name: Commit & push if changed
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/
          if git diff --staged --quiet; then
            echo "No changes to commit."
          else
            git commit -m "data: prices $(TZ=Asia/Seoul date +%Y-%m-%d)"
            git push
          fi
```

- [ ] **Step 2: 워크플로 핵심 내용 검증 (stdlib만 사용, 네트워크/YAML 의존 없음)**

Run:
```
python -c "import pathlib; t=pathlib.Path('.github/workflows/fetch-prices.yml').read_text(encoding='utf-8'); assert '0 23 * * 0-4' in t; assert 'contents: write' in t; assert 'workflow_dispatch' in t; assert 'python -m stock_price.main' in t; print('workflow ok')"
```
Expected: `workflow ok`

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/fetch-prices.yml
git commit -m "ci: add scheduled workflow to fetch prices and push daily" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: README + 통합 검증

**Files:**
- Create: `README.md`

- [ ] **Step 1: README 작성**

`README.md`:
````markdown
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
````

- [ ] **Step 2: 전체 단위 테스트 재확인**

Run: `pytest -v`
Expected: PASS (24 passed)

- [ ] **Step 3: 통합 실행 (네트워크 필요 — FDR 실제 조회)**

Run: `python -m stock_price.main`
Expected: 종료코드 0. `data/<오늘 KST 날짜>.json` 파일이 생성되고, `prices`에 `tickers.json`의 종목들이 채워진다(일부 종목이 일시적으로 실패하면 `errors`에 기록될 수 있음 — 정상).

확인:
```
python -c "import json,glob; f=sorted(glob.glob('data/*.json'))[-1]; d=json.load(open(f,encoding='utf-8')); print(f, 'count=', d['count'], 'errors=', len(d['errors']))"
```
Expected: 파일 경로와 `count=`(1 이상), `errors=` 개수 출력. (전체 종목이 실패해 count=0이면 네트워크/심볼 문제이므로 조사한다.)

- [ ] **Step 4: 커밋 (README + 첫 데이터 파일)**

```bash
git add README.md data/
git commit -m "docs: add README; chore: first fetched price snapshot" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (작성자 체크리스트 — 계획 검토 결과)

**1. Spec coverage** — 스펙 각 절을 구현하는 태스크 매핑:
- §4 watchlist → Task 2 ✓ / fetcher → Task 5 ✓ / formatter → Task 3 ✓ / storage → Task 4 ✓ / main → Task 6 ✓
- §5 tickers.json → Task 1(샘플) + Task 2(로드) ✓
- §6 출력 스키마(run_date/fetched_at/count/prices/errors, price_date 구분) → Task 4(payload)+Task 3(record)+Task 6 ✓
- §7 통화·시장 추론(+오버라이드) → Task 3 ✓
- §8 부분 실패/전체 실패 종료코드/같은 날 덮어쓰기 → Task 6 + Task 4(overwrite 테스트) ✓
- §9 테스트 전략 → Task 2~6 테스트 ✓
- §10 워크플로(cron 0 23 * * 0-4, contents: write, workflow_dispatch, 변경 시에만 커밋) → Task 7 ✓
- §11 프로젝트 구조/산출물(pyproject, requirements, .gitignore, .gitkeep, README) → Task 1 + Task 8 ✓
- §12 의존성 → Task 1 ✓

**2. Placeholder scan** — TBD/TODO/"적절히 처리" 류 없음. 모든 코드 단계에 완전한 코드 포함 ✓

**3. Type consistency** — `Ticker(symbol,name,currency,market)`, `fetch_latest(symbol, reader, retries, sleep, backoff_seconds)`, `build_record(ticker, df)`, `day_file_path(run_date, data_dir)`, `build_payload(run_date, fetched_at, records, errors)`, `write_day_file(path, payload)`, `run(watchlist_path, data_dir, now, reader, sleep)` — 정의와 호출부 시그니처/이름 일치 확인 ✓ (`KST = timezone(timedelta(hours=9))`는 storage 테스트·main에서 동일 정의)
