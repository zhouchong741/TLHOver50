from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


DEFAULT_CATEGORY_URL = (
    "https://www.thelasthunt.com/c/all?brand_name=icebreaker%2CPatagonia&size_1=S%2CM%2CL&sort=discountDesc"
)


@dataclass(frozen=True)
class AppConfig:
    category_url: str
    min_discount: int
    state_file: Path
    site_dir: Path
    log_file: Path
    log_level: str
    pages_url: str
    deployed_at: str
    dry_run: bool
    timeout_seconds: float


def load_env() -> None:
    load_dotenv()


def env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default
