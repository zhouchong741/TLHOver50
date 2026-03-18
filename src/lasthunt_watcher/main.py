from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

from .config import AppConfig, DEFAULT_CATEGORY_URL, env_or_default, load_env
from .scraper import LastHuntScraper, build_retry_session
from .site_builder import PAGE_TITLE, build_site
from .state import detect_count_change, load_state, save_state


def parse_args(argv: list[str] | None = None) -> AppConfig:
    load_env()

    parser = argparse.ArgumentParser(
        description="Watch The Last Hunt Icebreaker + Patagonia deals and build a GitHub Pages dashboard."
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
        "--site-dir",
        default=env_or_default("LASTHUNT_SITE_DIR", "site"),
        help="Path to the generated static site directory.",
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
        "--pages-url",
        default=env_or_default("LASTHUNT_PAGES_URL", ""),
        help="Public GitHub Pages URL included in notifications and site metadata.",
    )
    parser.add_argument(
        "--deployed-at",
        default=env_or_default("LASTHUNT_DEPLOYED_AT", ""),
        help="Deployment timestamp shown on the generated page.",
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
        site_dir=Path(args.site_dir),
        log_file=Path(args.log_file),
        log_level=args.log_level.upper(),
        pages_url=args.pages_url.rstrip("/"),
        deployed_at=args.deployed_at,
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

    session = build_retry_session()
    scraper = LastHuntScraper(
        session=session,
        category_url=config.category_url,
        min_discount=config.min_discount,
        timeout_seconds=config.timeout_seconds,
    )

    products, metrics = scraper.scrape()
    site_info = build_site(
        products=products,
        output_dir=config.site_dir,
        category_url=config.category_url,
        min_discount=config.min_discount,
        pages_url=config.pages_url,
        deployed_at=config.deployed_at,
    )
    state = load_state(config.state_file)
    count_change, next_state = detect_count_change(products, state)
    previous_count = next_state["summary"]["previous_count"]

    logger.info(
        (
            "Run summary: raw_hits=%s unique_products=%s filtered_products=%s "
            "pages=%s previous_count=%s current_count=%s count_changed=%s site_dir=%s"
        ),
        metrics["raw_hits"],
        metrics["unique_products"],
        metrics["filtered_products"],
        metrics["total_pages"],
        previous_count,
        next_state["summary"]["current_count"],
        bool(count_change),
        site_info["site_dir"],
    )

    if config.dry_run:
        logger.info("Dry-run mode enabled, skipping state write.")
        return 0

    _save_notification_summary(
        path=config.state_file.parent / "notification.json",
        current_count=len(products),
        previous_count=previous_count,
        pages_url=config.pages_url,
        category_url=config.category_url,
        generated_at=str(site_info["generated_at"]),
        deployed_at=str(site_info["deployed_at"]),
    )
    save_state(config.state_file, next_state)
    logger.info("State saved to %s", config.state_file)
    return 0


def _save_notification_summary(
    path: Path,
    current_count: int,
    previous_count: int | None,
    pages_url: str,
    category_url: str,
    generated_at: str,
    deployed_at: str,
) -> None:
    if previous_count is None:
        change_label = "首次部署"
        delta = 0
    else:
        delta = current_count - previous_count
        if delta > 0:
            change_label = f"增加 {delta}"
        elif delta < 0:
            change_label = f"减少 {abs(delta)}"
        else:
            change_label = "无变化"

    summary = {
        "title": PAGE_TITLE,
        "current_count": current_count,
        "previous_count": previous_count,
        "delta": delta,
        "change_label": change_label,
        "pages_url": pages_url,
        "category_url": category_url,
        "generated_at": generated_at,
        "deployed_at": deployed_at,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
