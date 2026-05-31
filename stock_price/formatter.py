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
