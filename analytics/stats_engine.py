from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from .trade_logger import TradeLogger, TradeRecord


@dataclass
class StatsSnapshot:
    total_trades: int
    winrate: float
    average_r: float
    net_pnl: float
    max_drawdown_pct: float
    pnl_by_day: Dict[str, float]


class StatsEngine:
    """Compute lightweight analytics based on the persisted trades."""

    def __init__(self, trade_logger: TradeLogger) -> None:
        self._logger = trade_logger

    def compute(self) -> StatsSnapshot:
        trades = self._logger.read_all()
        if not trades:
            return StatsSnapshot(0, 0.0, 0.0, 0.0, 0.0, {})

        total_trades = len(trades)
        winners = sum(1 for t in trades if t.pnl > 0)
        winrate = winners / total_trades if total_trades else 0.0
        average_r = sum(t.r_multiple for t in trades) / total_trades if total_trades else 0.0
        net_pnl = sum(t.pnl for t in trades)
        pnl_by_day = self._aggregate_daily(trades)
        max_drawdown_pct = self._compute_drawdown(trades)

        return StatsSnapshot(
            total_trades=total_trades,
            winrate=winrate,
            average_r=average_r,
            net_pnl=net_pnl,
            max_drawdown_pct=max_drawdown_pct,
            pnl_by_day=pnl_by_day,
        )

    def _aggregate_daily(self, trades: List[TradeRecord]) -> Dict[str, float]:
        pnl_by_day: Dict[str, float] = defaultdict(float)
        for trade in trades:
            day = datetime.fromisoformat(trade.timestamp).date().isoformat()
            pnl_by_day[day] += trade.pnl
        return dict(pnl_by_day)

    def _compute_drawdown(self, trades: List[TradeRecord]) -> float:
        profit_curve = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for trade in trades:
            profit_curve += trade.pnl
            peak = max(peak, profit_curve)
            if peak > 0:
                dd = (peak - profit_curve) / peak
                max_drawdown = max(max_drawdown, dd)
        return max_drawdown

