from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from core.config_manager import BotConfig
from data.symbol_info import SymbolInfo


@dataclass
class RiskResult:
    qty: float
    entry_price: float
    sl_price: float
    tp_price: float
    risk_amount: float


class RiskManager:
    """Translate strategy signals into executable position sizes."""

    def __init__(self, config: BotConfig, symbol_info: SymbolInfo) -> None:
        self._config = config
        self._symbol_info = symbol_info

    def evaluate(
        self,
        *,
        entry_price: float,
        sl_price: float,
        tp_price: float,
    ) -> RiskResult:
        reference = self._config.risk_limits.reference_account_size_usdt
        risk_amount = reference * self._config.profile.risk_per_trade_pct
        stop_distance = abs(entry_price - sl_price)
        if stop_distance <= 0:
            raise ValueError("Stop distance must be positive")

        qty = risk_amount / stop_distance
        qty = self._apply_precision(qty)
        if qty < self._symbol_info.min_qty:
            raise ValueError("Position size below exchange minimum")

        return RiskResult(
            qty=qty,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            risk_amount=risk_amount,
        )

    def _apply_precision(self, qty: float) -> float:
        step = self._symbol_info.qty_step
        precision = int(round(1 / step))
        return (int(qty * precision) / precision)

