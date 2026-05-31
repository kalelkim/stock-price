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
