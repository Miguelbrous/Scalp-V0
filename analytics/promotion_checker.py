from __future__ import annotations

from dataclasses import dataclass

from core.config_manager import BotConfig

from .stats_engine import StatsEngine, StatsSnapshot


@dataclass
class PromotionStatus:
    demo_to_live_ready: bool
    scale_up_ready: bool
    details: str


class PromotionChecker:
    """Evaluates if demo performance is good enough to promote risk settings."""

    def __init__(self, config: BotConfig, stats_engine: StatsEngine) -> None:
        self._config = config
        self._stats_engine = stats_engine

    def evaluate(self) -> PromotionStatus:
        stats = self._stats_engine.compute()
        rules = self._config.promotion_rules
        demo_ready = (
            stats.total_trades >= rules.min_demo_trades
            and stats.net_pnl >= rules.min_net_profit_usdt
            and stats.max_drawdown_pct <= rules.max_drawdown_pct
        )
        scale_up = demo_ready and stats.winrate >= 0.55 and stats.average_r >= 1.0

        detail = (
            f"Trades={stats.total_trades}, Winrate={stats.winrate:.2%}, "
            f"NetPnL={stats.net_pnl:.2f}, MaxDD={stats.max_drawdown_pct:.2%}"
        )
        return PromotionStatus(demo_to_live_ready=demo_ready, scale_up_ready=scale_up, details=detail)

