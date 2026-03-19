"""Executor on/off state (executor_enabled.json)."""
import json

from app.config import REPO_ROOT
from bt_utils.constants import EXECUTOR_ENABLED_FILENAME


def read_executor_enabled() -> bool:
    """True if executor_enabled.json has \"enabled\": true. Default True if file missing."""
    path = REPO_ROOT / EXECUTOR_ENABLED_FILENAME
    if not path.is_file():
        return True
    try:
        with open(path) as f:
            return json.load(f).get("enabled", True)
    except Exception:
        return True


def set_executor_enabled(enabled: bool) -> None:
    """Write executor_enabled.json. Raises on IO error."""
    path = REPO_ROOT / EXECUTOR_ENABLED_FILENAME
    with open(path, "w") as f:
        json.dump({"enabled": enabled}, f)
