"""Read/write app settings: tolerance offset, heartbeat enabled."""
import json

from app.config import REPO_ROOT

# Re-use core config for tolerance offset (file is under REPO_ROOT via cwd)
from app.core.config import (
    load_tolerance_offset,
    save_tolerance_offset,
    settings as core_settings,
)

HEARTBEAT_ENABLED_FILE = REPO_ROOT / "heartbeat_enabled.json"
DEFAULT_HEARTBEAT_ENABLED = True


def get_heartbeat_enabled() -> bool:
    """Read heartbeat on/off from file. Default True if file missing."""
    if not HEARTBEAT_ENABLED_FILE.is_file():
        return DEFAULT_HEARTBEAT_ENABLED
    try:
        with open(HEARTBEAT_ENABLED_FILE) as f:
            return json.load(f).get("enabled", DEFAULT_HEARTBEAT_ENABLED)
    except Exception:
        return DEFAULT_HEARTBEAT_ENABLED


def set_heartbeat_enabled(enabled: bool) -> None:
    """Write heartbeat on/off to file."""
    with open(HEARTBEAT_ENABLED_FILE, "w") as f:
        json.dump({"enabled": enabled}, f)


def set_tolerance_offset(value: float | str) -> bool:
    """Save tolerance offset to file and update in-memory core settings."""
    if not save_tolerance_offset(value):
        return False
    core_settings.TOLERANCE_OFFSET = load_tolerance_offset()
    return True


def set_heartbeat_enabled_safe(enabled: bool) -> None:
    """Write heartbeat enabled; no in-memory cache to update."""
    set_heartbeat_enabled(enabled)
