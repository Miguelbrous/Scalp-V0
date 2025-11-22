from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .config_manager import BotConfig


class BotMode(str, Enum):
    NORMAL = "NORMAL"
    COOLDOWN = "COOLDOWN"
    LIMITED = "LIMITED"
    HALT = "HALT"


@dataclass
class SessionStats:
    trading_day: str
    daily_pnl: float = 0.0
    daily_trades: int = 0
    consecutive_losses: int = 0


@dataclass
class EquityStats:
    cumulative_pnl: float = 0.0
    peak_equity: float = 0.0
    max_drawdown_pct: float = 0.0


@dataclass
class TradeResult:
    pnl: float
    timestamp: datetime
    fees: float = 0.0

    @property
    def net_pnl(self) -> float:
        return self.pnl - self.fees

    @property
    def is_loss(self) -> bool:
        return self.net_pnl < 0


class StateManager:
    """Keeps track of live performance and enforces coarse account protection states."""

    def __init__(
        self,
        config: BotConfig,
        initial_state: Optional[Dict[str, Any]] = None,
        *,
        now_provider=datetime.utcnow,
    ) -> None:
        self._config = config
        self._now = now_provider

        utc_today = self._current_day()
        self._session_stats = SessionStats(trading_day=utc_today)
        ref_balance = self._config.risk_limits.reference_account_size_usdt
        self._equity_stats = EquityStats(
            cumulative_pnl=0.0,
            peak_equity=ref_balance,
            max_drawdown_pct=0.0,
        )

        self._mode: BotMode = BotMode.NORMAL
        self._cooldown_until: datetime | None = None
        self._next_mode_after_cooldown: BotMode = BotMode.NORMAL
        self._limited_until: datetime | None = None
        self._limited_exit_equity: float | None = None
        self._internal_version: str = "0.0.1"
        self._cooldown_counters = {"short": 0, "long": 0}
        self._cooldown_enabled = True

        if initial_state:
            self._hydrate(initial_state)

    # ------------------------------------------------------------------
    def on_trade_closed(self, trade_result: TradeResult) -> None:
        """Update stats and trigger state transitions after a trade closes."""
        self._maybe_roll_daily_stats(trade_result.timestamp)

        pnl = trade_result.net_pnl
        self._session_stats.daily_pnl += pnl
        self._session_stats.daily_trades += 1
        self._session_stats.consecutive_losses = (
            self._session_stats.consecutive_losses + 1 if trade_result.is_loss else 0
        )

        self._equity_stats.cumulative_pnl += pnl
        self._update_drawdown_metrics()

        if self._session_stats.daily_pnl <= -self._max_daily_loss_abs():
            self._trigger_daily_loss_cooldown()
        elif (
            self._session_stats.consecutive_losses
            >= self._config.profile.max_consecutive_losses_for_cooldown
        ):
            self._trigger_short_cooldown()

        self._evaluate_global_drawdown()
        self._evaluate_limited_exit()

    def can_trade_now(self) -> Tuple[bool, str | None]:
        """Return whether the current mode allows opening a new position."""
        self._evaluate_timers()
        if self._mode == BotMode.HALT:
            return False, "HALT"
        if self._mode == BotMode.COOLDOWN:
            return False, "COOLDOWN"
        return True, None

    def current_mode(self) -> BotMode:
        self._evaluate_timers()
        return self._mode

    @property
    def session_stats(self) -> SessionStats:
        return self._session_stats

    @property
    def equity_stats(self) -> EquityStats:
        return self._equity_stats

    # ------------------------------------------------------------------
    def export_state(self) -> Dict[str, Any]:
        """Return a serialisable snapshot to be persisted."""
        return {
            "mode": self._mode.value,
            "session_stats": asdict(self._session_stats),
            "equity_stats": asdict(self._equity_stats),
            "cooldown_until": self._cooldown_until.isoformat() if self._cooldown_until else None,
            "next_mode_after_cooldown": self._next_mode_after_cooldown.value,
            "limited_until": self._limited_until.isoformat() if self._limited_until else None,
            "limited_exit_equity": self._limited_exit_equity,
            "internal_version": self._internal_version,
            "cooldown_counters": self._cooldown_counters,
        }

    # ------------------------------------------------------------------
    def _trigger_daily_loss_cooldown(self) -> None:
        if not self._cooldown_enabled:
            return
        minutes = self._config.risk_limits.cooldown_long_minutes
        self._cooldown_counters["long"] += 1
        self._enter_cooldown(minutes, next_mode=BotMode.LIMITED)

    def _trigger_short_cooldown(self) -> None:
        if not self._cooldown_enabled:
            return
        minutes = self._config.risk_limits.cooldown_short_minutes
        self._cooldown_counters["short"] += 1
        self._enter_cooldown(minutes, next_mode=BotMode.NORMAL)

    def _enter_cooldown(self, minutes: int, *, next_mode: BotMode) -> None:
        if minutes <= 0:
            self._mode = next_mode
            return
        self._mode = BotMode.COOLDOWN
        self._cooldown_until = self._now_utc() + timedelta(minutes=minutes)
        self._next_mode_after_cooldown = next_mode

        if next_mode == BotMode.LIMITED:
            self._limited_until = (
                self._cooldown_until
                + timedelta(minutes=self._config.risk_limits.limited_mode_duration_minutes)
            )
            current_equity = self._current_equity()
            recovery = (
                current_equity
                + self._config.risk_limits.reference_account_size_usdt
                * self._config.risk_limits.limited_mode_recovery_pct
            )
            self._limited_exit_equity = recovery

    def _evaluate_timers(self) -> None:
        now = self._now_utc()
        if self._mode == BotMode.COOLDOWN and self._cooldown_until and now >= self._cooldown_until:
            self._mode = self._next_mode_after_cooldown
            self._cooldown_until = None

        if self._mode == BotMode.LIMITED and self._limited_until and now >= self._limited_until:
            self._mode = BotMode.NORMAL
            self._limited_until = None
            self._limited_exit_equity = None

    def _evaluate_limited_exit(self) -> None:
        if self._mode == BotMode.LIMITED and self._limited_exit_equity:
            if self._current_equity() >= self._limited_exit_equity:
                self._mode = BotMode.NORMAL
                self._limited_exit_equity = None
                self._limited_until = None

    def _evaluate_global_drawdown(self) -> None:
        dd_pct = self._equity_stats.max_drawdown_pct
        if dd_pct >= self._config.risk_limits.global_drawdown_pct:
            self._mode = BotMode.HALT

    def _update_drawdown_metrics(self) -> None:
        ref_balance = self._config.risk_limits.reference_account_size_usdt
        current_equity = ref_balance + self._equity_stats.cumulative_pnl
        self._equity_stats.peak_equity = max(self._equity_stats.peak_equity, current_equity)

        if self._equity_stats.peak_equity <= 0:
            return
        drawdown = (
            self._equity_stats.peak_equity - current_equity
        ) / self._equity_stats.peak_equity
        self._equity_stats.max_drawdown_pct = max(self._equity_stats.max_drawdown_pct, drawdown)

    # ------------------------------------------------------------------
    def _max_daily_loss_abs(self) -> float:
        reference = self._config.risk_limits.reference_account_size_usdt
        return reference * self._config.profile.max_daily_loss_pct

    def _current_equity(self) -> float:
        reference = self._config.risk_limits.reference_account_size_usdt
        return reference + self._equity_stats.cumulative_pnl

    def _maybe_roll_daily_stats(self, timestamp: datetime) -> None:
        trading_day = timestamp.astimezone(timezone.utc).date().isoformat()
        if trading_day != self._session_stats.trading_day:
            self._session_stats = SessionStats(trading_day=trading_day)

    def _current_day(self) -> str:
        return self._now_utc().date().isoformat()

    def _now_utc(self) -> datetime:
        now = self._now()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)

    def _hydrate(self, payload: Dict[str, Any]) -> None:
        if "mode" in payload:
            self._mode = BotMode(payload["mode"])
        if "session_stats" in payload:
            self._session_stats = SessionStats(**payload["session_stats"])
        if "equity_stats" in payload:
            self._equity_stats = EquityStats(**payload["equity_stats"])
        if payload.get("cooldown_until"):
            self._cooldown_until = datetime.fromisoformat(payload["cooldown_until"])
        self._next_mode_after_cooldown = BotMode(payload.get("next_mode_after_cooldown", "NORMAL"))
        if payload.get("limited_until"):
            self._limited_until = datetime.fromisoformat(payload["limited_until"])
        self._limited_exit_equity = payload.get("limited_exit_equity")
        if payload.get("internal_version"):
            self._internal_version = payload["internal_version"]
        if payload.get("cooldown_counters"):
            self._cooldown_counters.update(payload["cooldown_counters"])

    # ------------------------------------------------------------------
    @property
    def internal_version(self) -> str:
        return self._internal_version

    def bump_internal_version(self) -> str:
        parts = self._internal_version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            self._internal_version = "0.0.1"
            return self._internal_version
        major, minor, patch = map(int, parts)
        patch += 1
        self._internal_version = f"{major}.{minor}.{patch}"
        return self._internal_version

    @property
    def cooldown_counters(self) -> Dict[str, int]:
        return self._cooldown_counters.copy()

    def current_cooldown_countdown(self) -> tuple[str | None, float]:
        """Return current cooldown type (SHORT/LONG) and minutes remaining."""
        self._evaluate_timers()
        if self._mode != BotMode.COOLDOWN or not self._cooldown_until:
            return None, 0.0
        now = self._now_utc()
        minutes_left = max(
            0.0, (self._cooldown_until - now).total_seconds() / 60.0
        )
        cooldown_type = (
            "LONG" if self._next_mode_after_cooldown == BotMode.LIMITED else "SHORT"
        )
        return cooldown_type, minutes_left
