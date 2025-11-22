from __future__ import annotations

from typing import Optional

from core.config import StrategyConfig, get_settings
from core.models import OrderIntent, TradingViewPayload


def build_intent_from_tv(payload: TradingViewPayload) -> Optional[OrderIntent]:
    """Traduce la alerta de TradingView en un OrderIntent listo para ejecutar."""
    settings = get_settings()
    strat: StrategyConfig
    try:
        strat = settings.strategies[payload.strategy]
    except KeyError:
        return None

    base_risk = strat.risk_per_trade or settings.default_risk_per_trade
    if payload.action == "entry":
        return _build_entry_intent(payload, strat, base_risk)
    if payload.action == "exit":
        return _build_exit_intent(payload, strat, base_risk)
    return None


def _build_entry_intent(
    payload: TradingViewPayload,
    strat: StrategyConfig,
    risk_perc: float,
) -> OrderIntent:
    long_side = payload.side == "long"
    sl_distance = payload.price * strat.default_sl_distance_pct
    tp_distance = payload.price * strat.default_tp_distance_pct
    sl = payload.price - sl_distance if long_side else payload.price + sl_distance
    tp = payload.price + tp_distance if long_side else payload.price - tp_distance
    return OrderIntent(
        symbol=strat.symbol,
        side="buy" if long_side else "sell",
        type=strat.order_type,
        entry_price=payload.price,
        stop_loss=sl,
        take_profit=tp,
        risk_perc=risk_perc,
        strategy=payload.strategy,
    )


def _build_exit_intent(
    payload: TradingViewPayload,
    strat: StrategyConfig,
    risk_perc: float,
) -> OrderIntent:
    # El cierre invierte la dirección original.
    close_side_buy = payload.side == "short"
    return OrderIntent(
        symbol=strat.symbol,
        side="buy" if close_side_buy else "sell",
        type="market",
        entry_price=payload.price,
        stop_loss=payload.price,  # placeholders: no se usan para el cierre
        take_profit=payload.price,
        risk_perc=risk_perc,
        strategy=payload.strategy,
    )
