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
