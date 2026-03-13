"""Load application settings from JSON config files."""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import AppSettings, DEFAULT_SETTINGS


def load_settings(config_path: str | None = None) -> AppSettings:
    """Load settings from JSON file or return defaults.

    Args:
        config_path: Optional path to a JSON file.

    Returns:
        Validated AppSettings object.
    """
    if not config_path:
        return DEFAULT_SETTINGS

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if path.suffix.lower() != ".json":
        raise ValueError("Only JSON config files are supported in this starter project.")

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return AppSettings.model_validate(payload)
