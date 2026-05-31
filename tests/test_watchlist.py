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
