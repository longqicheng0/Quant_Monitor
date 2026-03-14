"""Load application settings from JSON config files."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from config.settings import AppSettings, DEFAULT_SETTINGS


def load_settings(config_path: str | None = None) -> AppSettings:
    """Load settings from JSON file or return defaults.

    Args:
        config_path: Optional path to a JSON file.

    Returns:
        Validated AppSettings object.
    """
    if not config_path:
        # Return a fresh copy so runtime overrides do not mutate global defaults.
        return AppSettings.model_validate(DEFAULT_SETTINGS.model_dump())

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if path.suffix.lower() != ".json":
        raise ValueError("Only JSON config files are supported in this starter project.")

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config JSON parse error in {config_path}: {exc}") from exc

    try:
        return AppSettings.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Config validation error in {config_path}: {exc}") from exc
