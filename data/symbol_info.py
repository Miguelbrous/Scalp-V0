from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    base_asset: str
    quote_asset: str
    min_qty: float
    qty_step: float
    tick_size: float
    leverage: int
    margin_mode: str


_BTCUSDT_INFO = SymbolInfo(
    symbol="BTCUSDT",
    base_asset="BTC",
    quote_asset="USDT",
    min_qty=0.001,
    qty_step=0.001,
    tick_size=0.1,
    leverage=5,
    margin_mode="ISOLATED",
)

_SOLUSDT_INFO = SymbolInfo(
    symbol="SOLUSDT",
    base_asset="SOL",
    quote_asset="USDT",
    min_qty=0.1,
    qty_step=0.1,
    tick_size=0.001,
    leverage=3,
    margin_mode="ISOLATED",
)

_SYMBOL_MAP: Dict[str, SymbolInfo] = {
    _BTCUSDT_INFO.symbol: _BTCUSDT_INFO,
    _SOLUSDT_INFO.symbol: _SOLUSDT_INFO,
}


def get_symbol_info(symbol: str) -> SymbolInfo:
    """Return cached symbol metadata. Extend with API lookups in future versions."""
    info = _SYMBOL_MAP.get(symbol.upper())
    if not info:
        raise KeyError(f"Symbol metadata not found for {symbol}")
    return info
