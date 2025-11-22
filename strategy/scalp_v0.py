from __future__ import annotations

# ================================================================
# Scalp V0 - MOTOR CONGELADO
# ---------------------------------------------------------------
# Este modulo contiene la logica original de la estrategia V0.
# No se debe modificar salvo para corregir bugs confirmados.
# Nuevas estrategias se desarrollan primero en TradingView y solo
# se integran si cumplen PF > 1.3, 200+ trades y DD < 20 %.
# ================================================================

from dataclasses import dataclass
from datetime import datetime, time, timezone
import logging
from typing import List, Tuple

from core.config_manager import BotConfig
from data.market_data import MarketSnapshot

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    side: str  # LONG, SHORT, NO_TRADE
    entry_price: float
    sl_price: float
    tp_price: float
    time_stop_minutes: int
    reason: str | None = None


class ScalpV0Strategy:
    """First iteration of the scalping strategy, purely signal generation."""

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._params = config.strategy_params
        self._profile = config.profile
        self._sessions: List[Tuple[time, time]] = self._build_sessions(config.sessions.preferred)
        self._allow_offsession = config.sessions.allow_offsession_trades_if_high_quality

    def generate_signal(self, snapshot: MarketSnapshot) -> TradeSignal:
        if snapshot.atr < self._params.min_atr:
            logger.info(
                "NO_TRADE: ATR demasiado bajo (ATR=%.4f, min_atr=%.4f)",
                snapshot.atr,
                self._params.min_atr,
            )
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "ATR_TOO_LOW")

        if not self._is_in_session(snapshot.timestamp):
            if not self._allow_offsession:
                logger.info("NO_TRADE: fuera de sesiones preferidas")
                return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "OUT_OF_SESSION")
            if not self._is_high_quality_offsession(snapshot):
                logger.info("NO_TRADE: fuera de sesión y sin condiciones de alta calidad")
                return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "OFFSESSION_LOW_QUALITY")

        if abs(snapshot.vwap_distance_pct) > self._params.max_vwap_distance_pct:
            logger.info(
                "NO_TRADE: precio %.2f%% lejos de VWAP (máximo %.2f%%)",
                snapshot.vwap_distance_pct,
                self._params.max_vwap_distance_pct,
            )
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "DISTANT_FROM_VWAP")

        ema_distance_pct = abs(snapshot.price - snapshot.ema_fast) / snapshot.price * 100
        if ema_distance_pct > self._params.max_price_ema_distance_pct:
            logger.info(
                "NO_TRADE: precio %.2f%% lejos de EMA rápida (máximo %.2f%%)",
                ema_distance_pct,
                self._params.max_price_ema_distance_pct,
            )
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "FAR_FROM_EMA")

        if snapshot.volatility is not None and snapshot.volatility < self._params.min_volatility:
            logger.info(
                "NO_TRADE: volatilidad insuficiente (%.5f < %.5f)",
                snapshot.volatility,
                self._params.min_volatility,
            )
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "VOLATILITY_TOO_LOW")

        if self._profile.name == "PROFILE_PROD" and abs(snapshot.vwap_distance_pct) > 0.5:
            logger.info(
                "NO_TRADE: precio muy alejado de VWAP (distancia=%.2f%%, umbral=0.5%%)",
                snapshot.vwap_distance_pct,
            )
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "DISTANT_FROM_VWAP")

        setup = self._detect_setup(snapshot)
        if setup is None:
            return TradeSignal("NO_TRADE", snapshot.price, snapshot.price, snapshot.price, 0, "NO_SETUP")

        side = setup
        entry = snapshot.price
        sl, tp = self._build_levels(side, entry, snapshot.atr)
        return TradeSignal(
            side=side,
            entry_price=entry,
            sl_price=sl,
            tp_price=tp,
            time_stop_minutes=self._params.time_stop_minutes,
        )

    def _detect_setup(self, snapshot: MarketSnapshot) -> str | None:
        current = snapshot.current_candle
        prev = snapshot.previous_candle
        if current is None or prev is None:
            logger.info("NO_TRADE: sin vela previa disponible para confirmar pullback")
            return None

        if snapshot.ema_fast > snapshot.ema_slow and snapshot.price > snapshot.vwap:
            if not self._rsi_allows_long(snapshot.rsi):
                logger.info("NO_TRADE: RSI fuera de rango para largos (%.2f)", snapshot.rsi or -1)
                return None
            if self._pullback_long(prev, current):
                return "LONG"
            logger.info("NO_TRADE: patrón de pullback largo no confirmado")
            return None

        if snapshot.ema_fast < snapshot.ema_slow and snapshot.price < snapshot.vwap:
            if not self._rsi_allows_short(snapshot.rsi):
                logger.info("NO_TRADE: RSI fuera de rango para cortos (%.2f)", snapshot.rsi or -1)
                return None
            if self._pullback_short(prev, current):
                return "SHORT"
            logger.info("NO_TRADE: patrón de pullback corto no confirmado")
            return None

        logger.info("NO_TRADE: contexto de tendencia no válido para pullback")
        return None

    def _build_levels(self, side: str, entry: float, atr: float) -> tuple[float, float]:
        sl_distance = atr * self._params.atr_multiplier_sl
        tp_distance = atr * self._params.atr_multiplier_tp
        if side == "LONG":
            return entry - sl_distance, entry + tp_distance
        return entry + sl_distance, entry - tp_distance

    # ------------------------------------------------------------------
    def _build_sessions(self, preferred: List[dict]) -> List[Tuple[time, time]]:
        sessions: List[Tuple[time, time]] = []
        for window in preferred:
            start = datetime.strptime(window["start"], "%H:%M").time()
            end = datetime.strptime(window["end"], "%H:%M").time()
            sessions.append((start, end))
        return sessions

    def _is_in_session(self, timestamp: datetime) -> bool:
        if not self._sessions:
            return True
        ts = timestamp.astimezone(timezone.utc).time()
        for start, end in self._sessions:
            if start <= end:
                if start <= ts <= end:
                    return True
            else:
                if ts >= start or ts <= end:
                    return True
        return False

    def _is_high_quality_offsession(self, snapshot: MarketSnapshot) -> bool:
        atr_condition = snapshot.atr >= self._params.min_atr * 1.5
        vwap_condition = abs(snapshot.vwap_distance_pct) <= self._params.max_vwap_distance_pct / 2
        rsi_condition = snapshot.rsi is not None and (
            snapshot.rsi <= self._params.rsi_short_min or snapshot.rsi >= self._params.rsi_long_max
        )
        return atr_condition and vwap_condition and rsi_condition

    def _pullback_long(self, prev, current) -> bool:
        tolerance = self._params.pullback_tolerance_pct / 100
        if prev.low > prev.ema_fast:
            return False
        if prev.close >= prev.open:
            return False
        if current.close <= current.open:
            return False
        if current.close <= prev.high:
            return False
        if current.close <= current.ema_fast:
            return False
        if abs(current.close - current.ema_fast) > current.close * tolerance:
            return False
        return True

    def _pullback_short(self, prev, current) -> bool:
        tolerance = self._params.pullback_tolerance_pct / 100
        if prev.high < prev.ema_fast:
            return False
        if prev.close <= prev.open:
            return False
        if current.close >= current.open:
            return False
        if current.close >= prev.low:
            return False
        if current.close >= current.ema_fast:
            return False
        if abs(current.close - current.ema_fast) > current.close * tolerance:
            return False
        return True

    def _rsi_allows_long(self, value: float | None) -> bool:
        if value is None:
            return True
        return self._params.rsi_long_min <= value <= self._params.rsi_long_max

    def _rsi_allows_short(self, value: float | None) -> bool:
        if value is None:
            return True
        return self._params.rsi_short_min <= value <= self._params.rsi_short_max
