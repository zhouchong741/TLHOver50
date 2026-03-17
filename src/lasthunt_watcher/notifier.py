from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

import requests

from .models import ProductChange, format_price


LOGGER = logging.getLogger(__name__)
FIELD_LABELS = {
    "original_price": "原价",
    "sale_price": "折后价",
    "discount_percent": "折扣",
}


@dataclass
class FeishuNotifier:
    session: requests.Session
    webhook_url: str
    dry_run: bool = False
    batch_size: int = 5

    def send_changes(self, changes: Iterable[ProductChange]) -> None:
        change_list = list(changes)
        if not change_list:
            LOGGER.info("No Feishu notification needed.")
            return

        for start in range(0, len(change_list), self.batch_size):
            batch = change_list[start : start + self.batch_size]
            message = self._build_message(batch)
            if self.dry_run:
                LOGGER.info("Dry-run Feishu payload:\n%s", message)
                continue

            response = self.session.post(
                self.webhook_url,
                json={"msg_type": "text", "content": {"text": message}},
                timeout=20,
            )
            response.raise_for_status()
            LOGGER.info("Sent Feishu notification for %s change(s).", len(batch))

    def _build_message(self, changes: list[ProductChange]) -> str:
        lines = [f"The Last Hunt Icebreaker 监控提醒，共 {len(changes)} 条"]
        for index, change in enumerate(changes, start=1):
            lines.append("")
            lines.append(f"{index}. {self._render_title(change)}")
            lines.extend(self._render_body(change))
        return "\n".join(lines)

    def _render_title(self, change: ProductChange) -> str:
        if change.kind == "new":
            return f"[新增] {change.product.name}"
        field_text = ", ".join(FIELD_LABELS.get(field, field) for field in change.changed_fields)
        return f"[变更:{field_text}] {change.product.name}"

    def _render_body(self, change: ProductChange) -> list[str]:
        current = change.product
        if change.kind == "new" or not change.previous:
            return [
                f"原价: {format_price(current.original_price_cents)}",
                f"折后价: {format_price(current.sale_price_cents)}",
                f"折扣: {current.discount_percent}%",
                f"详情: {current.detail_url}",
                f"图片: {current.image_url}",
            ]

        previous = change.previous
        return [
            (
                "原价: "
                f"{format_price(int(previous['original_price_cents']))}"
                f" -> {format_price(current.original_price_cents)}"
            ),
            (
                "折后价: "
                f"{format_price(int(previous['sale_price_cents']))}"
                f" -> {format_price(current.sale_price_cents)}"
            ),
            (
                "折扣: "
                f"{int(previous['discount_percent'])}%"
                f" -> {current.discount_percent}%"
            ),
            f"详情: {current.detail_url}",
            f"图片: {current.image_url}",
        ]
