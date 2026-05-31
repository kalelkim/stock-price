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
