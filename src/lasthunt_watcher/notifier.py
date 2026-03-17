from __future__ import annotations

from dataclasses import dataclass
import logging

import requests

from .models import CountChange


LOGGER = logging.getLogger(__name__)


@dataclass
class FeishuNotifier:
    session: requests.Session
    webhook_url: str
    dry_run: bool = False

    def send_count_change(
        self,
        change: CountChange | None,
        current_count: int,
        pages_url: str,
        category_url: str,
    ) -> None:
        if change is None:
            LOGGER.info("Product count unchanged, no Feishu notification needed.")
            return

        message = self._build_message(
            change=change,
            current_count=current_count,
            pages_url=pages_url,
            category_url=category_url,
        )
        if self.dry_run:
            LOGGER.info("Dry-run Feishu payload:\n%s", message)
            return

        response = self.session.post(
            self.webhook_url,
            json={"msg_type": "text", "content": {"text": message}},
            timeout=20,
        )
        response.raise_for_status()
        LOGGER.info("Sent Feishu notification for product count change.")

    def _build_message(
        self,
        change: CountChange,
        current_count: int,
        pages_url: str,
        category_url: str,
    ) -> str:
        lines = [
            "The Last Hunt Icebreaker >=50% 商品数量变更",
            f"产品总数: {current_count}",
            (
                f"变化: {change.direction_label} {change.abs_delta} "
                f"({change.previous_count} -> {change.current_count})"
            ),
        ]
        if pages_url:
            lines.append(f"页面: {pages_url}")
        lines.append(f"来源: {category_url}")
        return "\n".join(lines)
