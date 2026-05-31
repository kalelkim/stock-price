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
