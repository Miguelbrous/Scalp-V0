from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Protocol


class StatefulComponent(Protocol):
    def export_state(self) -> Dict[str, Any]:
        ...


DEFAULT_STATE_PATH = Path("config/state.json")


def save_state(state_manager: StatefulComponent, path: Path | str = DEFAULT_STATE_PATH) -> None:
    """Persist the current state to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(state_manager.export_state(), f, indent=2)


def load_state(path: Path | str = DEFAULT_STATE_PATH) -> Dict[str, Any] | None:
    """Load previous bot state if available."""
    target = Path(path)
    if not target.exists():
        return None
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)

