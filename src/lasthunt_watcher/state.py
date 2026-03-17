from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .models import ProductChange, ProductSnapshot


STATE_VERSION = 1


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": STATE_VERSION, "items": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid state file format: {path}")
    data.setdefault("version", STATE_VERSION)
    data.setdefault("items", {})
    return data


def detect_changes(
    products: list[ProductSnapshot], state: dict[str, object]
) -> tuple[list[ProductChange], dict[str, object]]:
    items = state.get("items", {})
    if not isinstance(items, dict):
        raise ValueError("State 'items' must be a mapping.")

    updated_items = dict(items)
    changes: list[ProductChange] = []

    for product in products:
        record = product.to_state_record()
        record["last_seen_at"] = _utc_now()
        previous = updated_items.get(product.object_id)

        if previous is None:
            changes.append(
                ProductChange(
                    kind="new",
                    product=product,
                    changed_fields=("new",),
                    previous=None,
                )
            )
            updated_items[product.object_id] = record
            continue

        changed_fields: list[str] = []
        if int(previous.get("original_price_cents", -1)) != product.original_price_cents:
            changed_fields.append("original_price")
        if int(previous.get("sale_price_cents", -1)) != product.sale_price_cents:
            changed_fields.append("sale_price")
        if int(previous.get("discount_percent", -1)) != product.discount_percent:
            changed_fields.append("discount_percent")

        if changed_fields:
            changes.append(
                ProductChange(
                    kind="updated",
                    product=product,
                    changed_fields=tuple(changed_fields),
                    previous=dict(previous),
                )
            )

        updated_items[product.object_id] = record

    next_state = {
        "version": STATE_VERSION,
        "updated_at": _utc_now(),
        "items": updated_items,
    }
    return changes, next_state


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

