"""Load project settings from config.yaml."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict:
    """Read config.yaml (default: the one in the project root) and return it as a dict."""
    path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(path: str | Path) -> Path:
    """Turn a path from config.yaml into an absolute path (relative paths are from the project root)."""
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path
