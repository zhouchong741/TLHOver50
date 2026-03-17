from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from .config import AppConfig, DEFAULT_CATEGORY_URL, env_or_default, load_env
from .notifier import FeishuNotifier
from .scraper import LastHuntScraper, build_retry_session
from .state import detect_changes, load_state, save_state


def parse_args(argv: list[str] | None = None) -> AppConfig:
    load_env()

    parser = argparse.ArgumentParser(
        description="Watch The Last Hunt Icebreaker deals and push changes to Feishu."
    )
    parser.add_argument(
        "--category-url",
        default=env_or_default("LASTHUNT_CATEGORY_URL", DEFAULT_CATEGORY_URL),
        help="Category URL to scrape.",
    )
    parser.add_argument(
        "--min-discount",
        type=int,
        default=int(env_or_default("LASTHUNT_MIN_DISCOUNT", "50")),
        help="Minimum discount percentage to keep.",
    )
    parser.add_argument(
        "--state-file",
        default=env_or_default("LASTHUNT_STATE_FILE", "data/state.json"),
        help="Path to the dedupe state file.",
    )
    parser.add_argument(
        "--log-file",
        default=env_or_default("LASTHUNT_LOG_FILE", "logs/lasthunt_watcher.log"),
        help="Path to the log file.",
    )
    parser.add_argument(
        "--log-level",
        default=env_or_default("LASTHUNT_LOG_LEVEL", "INFO"),
        help="Logging level.",
    )
    parser.add_argument(
        "--feishu-webhook-url",
        default=env_or_default("FEISHU_WEBHOOK_URL", ""),
        help="Override Feishu webhook URL.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and diff only, do not send Feishu message or persist state.",
    )

    args = parser.parse_args(argv)
    return AppConfig(
        category_url=args.category_url,
        min_discount=args.min_discount,
        state_file=Path(args.state_file),
        log_file=Path(args.log_file),
        log_level=args.log_level.upper(),
        feishu_webhook_url=args.feishu_webhook_url,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
    )


def setup_logging(level: str, log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    setup_logging(config.log_level, config.log_file)
    logger = logging.getLogger(__name__)

    if not config.dry_run and not config.feishu_webhook_url:
        raise SystemExit("FEISHU_WEBHOOK_URL is required unless --dry-run is used.")

    session = build_retry_session()
    scraper = LastHuntScraper(
        session=session,
        category_url=config.category_url,
        min_discount=config.min_discount,
        timeout_seconds=config.timeout_seconds,
    )

    products, metrics = scraper.scrape()
    state = load_state(config.state_file)
    changes, next_state = detect_changes(products, state)

    logger.info(
        "Run summary: raw_hits=%s unique_products=%s filtered_products=%s pages=%s changes=%s",
        metrics["raw_hits"],
        metrics["unique_products"],
        metrics["filtered_products"],
        metrics["total_pages"],
        len(changes),
    )

    notifier = FeishuNotifier(
        session=session,
        webhook_url=config.feishu_webhook_url,
        dry_run=config.dry_run,
    )
    notifier.send_changes(changes)

    if config.dry_run:
        logger.info("Dry-run mode enabled, skipping state write.")
        return 0

    save_state(config.state_file, next_state)
    logger.info("State saved to %s", config.state_file)
    return 0

