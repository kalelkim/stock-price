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
