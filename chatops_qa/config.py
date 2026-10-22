"""Environment-based configuration for the local ChatOps service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """Settings are read once at process start so runs use a consistent config."""

    project_root: Path = PROJECT_ROOT
    database_path: Path = _path_from_env(
        "DATABASE_PATH", PROJECT_ROOT / "data" / "chatops.sqlite3"
    )
    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    sauce_demo_base_url: str = os.getenv(
        "SAUCEDEMO_BASE_URL", "https://www.saucedemo.com/"
    )
    sauce_demo_username: str = os.getenv("SAUCEDEMO_USERNAME", "standard_user")
    sauce_demo_password: str = os.getenv("SAUCEDEMO_PASSWORD", "secret_sauce")
    run_timeout_seconds: int = int(os.getenv("TEST_RUN_TIMEOUT_SECONDS", "900"))


settings = Settings()
