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
