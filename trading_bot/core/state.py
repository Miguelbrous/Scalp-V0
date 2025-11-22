from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class PositionInfo:
    symbol: str
    strategy: str
    side: str
    qty: float
    entry_price: float


ACTIVE_POSITIONS: Dict[Tuple[str, str], PositionInfo] = {}


def _key(symbol: str, strategy: str) -> Tuple[str, str]:
    return symbol.upper(), strategy


def is_position_open(symbol: str, strategy: str) -> bool:
    return _key(symbol, strategy) in ACTIVE_POSITIONS


def mark_position_open(symbol: str, strategy: str, side: str, qty: float, entry_price: float) -> None:
    ACTIVE_POSITIONS[_key(symbol, strategy)] = PositionInfo(symbol, strategy, side, qty, entry_price)


def mark_position_closed(symbol: str, strategy: str) -> None:
    ACTIVE_POSITIONS.pop(_key(symbol, strategy), None)


def get_open_positions():
    return list(ACTIVE_POSITIONS.values())


def get_position(symbol: str, strategy: str) -> PositionInfo | None:
    return ACTIVE_POSITIONS.get(_key(symbol, strategy))
