"""App settings: current user, theme, density. Live in ``.backlogdesk/settings.json``, never in the store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULTS: Dict[str, Any] = dict(currentUser=None, theme="dark", density="compact")
CHOICES = dict(theme=("dark", "light"), density=("compact", "comfortable"))


class Settings:
    def __init__(self, folder: Optional[Path]):
        self.file = Path(folder) / "settings.json" if folder else None
        self.values: Dict[str, Any] = dict(DEFAULTS)
        if self.file is not None:
            try:
                saved = json.loads(self.file.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self.values.update({k: v for k, v in saved.items() if k in DEFAULTS})
            except (OSError, ValueError):
                pass

    def set(self, key: str, value: Any, people: Optional[Dict[str, Any]] = None) -> None:
        if key not in DEFAULTS:
            raise ValueError(f"unknown setting {key!r}")
        if key in CHOICES and value not in CHOICES[key]:
            raise ValueError(f"{key} must be one of {', '.join(CHOICES[key])}")
        if key == "currentUser" and value is not None and people is not None and value not in people:
            raise ValueError(f"{value!r} is not in people")
        self.values[key] = value
        if self.file is not None:
            from .store import atomic_write

            atomic_write(self.file, json.dumps(self.values, indent=2) + "\n")
