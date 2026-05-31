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


def test_korean_six_char_with_letter_is_krx_krw():
    # 신형우선주·일부 ETF는 6자리에 알파벳이 섞인다 (예: 0051G0, 0190Y0)
    assert infer_market_currency("0051G0") == ("KRX", "KRW")
    assert infer_market_currency("0190Y0") == ("KRX", "KRW")


def test_us_alpha_ticker_not_six_digit_is_us_usd():
    # ETN(이턴 코퍼레이션)처럼 알파벳 티커는 US/USD로 유지되어야 한다
    assert infer_market_currency("ETN") == ("US", "USD")


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


def test_build_record_zero_previous_close_change_pct_none():
    t = Ticker(symbol="AAPL", name="Apple")
    df = _df([0.0, 110.0], dates=["2026-05-28", "2026-05-29"])
    rec = build_record(t, df)
    assert rec["previous_close"] == 0.0
    assert rec["change"] == 110.0
    assert rec["change_pct"] is None


def test_build_record_nan_volume_becomes_none():
    t = Ticker(symbol="AAPL", name="Apple")
    df = _df([100.0, 110.0], volumes=[1000.0, float("nan")])
    rec = build_record(t, df)
    assert rec["volume"] is None


def test_non_six_digit_numeric_is_us_usd():
    assert infer_market_currency("7203") == ("US", "USD")


def test_build_record_rounds_float32_noise():
    t = Ticker(symbol="AAPL", name="Apple")
    df = _df([300.0, 312.05999755859375], dates=["2026-05-28", "2026-05-29"])
    rec = build_record(t, df)
    assert rec["close"] == 312.06
    assert rec["previous_close"] == 300.0
    assert rec["change"] == 12.06
