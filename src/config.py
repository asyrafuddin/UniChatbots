"""Load project settings from config.yaml (plus optional overrides, e.g. config.space.yaml on the HF Space)."""

import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OVERRIDES_ENV = "APP_CONFIG_OVERRIDES"  # set to e.g. config.space.yaml to change a few settings on one machine


def merge(base: dict, overrides: dict) -> dict:
    """Return base with overrides applied; nested sections are merged key by key."""
    merged = dict(base)
    for key, value in overrides.items():
        merged[key] = merge(base[key], value) if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    return merged


def load_config(path: str | Path | None = None) -> dict:
    """Read config.yaml (default: the one in the project root), then apply $APP_CONFIG_OVERRIDES if set."""
    path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if os.environ.get(OVERRIDES_ENV):
        with open(resolve_path(os.environ[OVERRIDES_ENV]), encoding="utf-8") as f:
            cfg = merge(cfg, yaml.safe_load(f) or {})
    return cfg


def require_env(name: str) -> str:
    """Return a secret from the environment or .env in the project root, with a clear error if missing."""
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to {PROJECT_ROOT / '.env'} (see .env.example).")
    return value


def resolve_path(path: str | Path) -> Path:
    """Turn a path from config.yaml into an absolute path (relative paths are from the project root)."""
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path
