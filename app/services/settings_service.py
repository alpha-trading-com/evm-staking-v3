"""Tolerance offset persistence (tolerance_offset.json / core settings)."""
from app.core.config import (
    load_tolerance_offset,
    save_tolerance_offset,
    settings as core_settings,
)


def set_tolerance_offset(value: float | str) -> bool:
    """Save tolerance offset to file and update in-memory core settings."""
    if not save_tolerance_offset(value):
        return False
    core_settings.TOLERANCE_OFFSET = load_tolerance_offset()
    return True
