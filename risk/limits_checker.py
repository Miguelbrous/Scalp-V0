from __future__ import annotations

from dataclasses import dataclass
import logging

from core.config_manager import BotConfig
from core.state_manager import BotMode, StateManager
from data.market_data import MarketSnapshot

logger = logging.getLogger(__name__)


@dataclass
class LimitCheckResult:
    allow_trade: bool
    reason: str | None = None


class LimitsChecker:
    """Applies pre-trade guardrails before sending any new orders."""

    def __init__(self, config: BotConfig, state_manager: StateManager) -> None:
        self._config = config
        self._state_manager = state_manager
        self._enforce_daily_loss = True

    def evaluate(self, snapshot: MarketSnapshot) -> LimitCheckResult:
        allow, reason = self._state_manager.can_trade_now()
        if not allow:
            logger.info("LIMIT_BLOCK: %s activo en state_manager", reason)
            return LimitCheckResult(False, reason)

        stats = self._state_manager.session_stats
        ref = self._config.risk_limits.reference_account_size_usdt
        max_daily_loss = ref * self._config.profile.max_daily_loss_pct
        current_mode = self._state_manager.current_mode()
        if (
            self._enforce_daily_loss
            and stats.daily_pnl <= -max_daily_loss
            and current_mode != BotMode.LIMITED
        ):
            logger.info(
                "LIMIT_BLOCK: se alcanzó max_daily_loss_pct (pnl=%.2f límite=%.2f)",
                stats.daily_pnl,
                -max_daily_loss,
            )
            return LimitCheckResult(False, "DAILY_LOSS_LIMIT")

        if stats.daily_trades >= self._config.profile.max_daily_trades:
            logger.info(
                "LIMIT_BLOCK: se alcanzó max_daily_trades (%s)",
                self._config.profile.max_daily_trades,
            )
            return LimitCheckResult(False, "DAILY_TRADE_LIMIT")

        if snapshot.atr < self._config.strategy_params.min_atr:
            logger.info(
                "LIMIT_BLOCK: ATR insuficiente en limits_checker (ATR=%.4f, min=%.4f)",
                snapshot.atr,
                self._config.strategy_params.min_atr,
            )
            return LimitCheckResult(False, "MARKET_TOO_DEAD")

        if abs(snapshot.vwap_distance_pct) > 1.5:
            # Avoid chasing extended price away from VWAP for the first iteration of V0.
            logger.info(
                "LIMIT_BLOCK: precio %.2f%% alejado de VWAP (umbral 1.5%%)",
                snapshot.vwap_distance_pct,
            )
            return LimitCheckResult(False, "EXTENDED_FROM_VWAP")

        return LimitCheckResult(True, None)
