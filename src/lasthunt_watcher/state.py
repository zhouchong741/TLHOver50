from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .models import CountChange, ProductSnapshot


STATE_VERSION = 2


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": STATE_VERSION, "summary": {}, "items": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid state file format: {path}")
    data.setdefault("version", STATE_VERSION)
    data.setdefault("summary", {})
    data.setdefault("items", {})
    return data


def detect_count_change(
    products: list[ProductSnapshot], state: dict[str, object]
) -> tuple[CountChange | None, dict[str, object]]:
    previous_count = _get_previous_count(state)
    current_items = {}

    for product in products:
        record = product.to_state_record()
        record["last_seen_at"] = _utc_now()
        current_items[product.object_id] = record

    current_count = len(products)
    count_change = None
    if previous_count is not None and current_count != previous_count:
        count_change = CountChange(
            previous_count=previous_count,
            current_count=current_count,
        )

    next_state = {
        "version": STATE_VERSION,
        "updated_at": _utc_now(),
        "summary": {
            "current_count": current_count,
            "previous_count": previous_count,
        },
        "items": current_items,
    }
    return count_change, next_state


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_previous_count(state: dict[str, object]) -> int | None:
    version = int(state.get("version", 0) or 0)
    if version < STATE_VERSION:
        return None

    summary = state.get("summary", {})
    if isinstance(summary, dict) and summary.get("current_count") is not None:
        return int(summary["current_count"])

    return None
