from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, status

from core import journal, state
from core.config import get_settings, get_strategy_config
from core.exchange import get_balance, get_client, place_order_market
from core.models import OrderResult, TradingViewPayload
from core.risk import RiskError, compute_position_size
from strategies.signal_router import build_intent_from_tv

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/tradingview")
async def tradingview_webhook(payload: TradingViewPayload):
    settings = get_settings()
    if payload.secret != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret invalido.")

    journal.log_signal(payload)

    intent = build_intent_from_tv(payload)
    if intent is None:
        return {"status": "ignored", "detail": "strategy_not_configured"}

    client = get_client(settings)

    if payload.action == "entry":
        if state.is_position_open(intent.symbol, intent.strategy):
            return {"status": "already_open"}
        try:
            balance = get_balance(client)
        except RuntimeError as exc:
            logger.error("No se pudo obtener el balance: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        try:
            qty = compute_position_size(balance, intent.risk_perc, intent.entry_price, intent.stop_loss)
        except RiskError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        strat_cfg = get_strategy_config(intent.strategy)
        if strat_cfg.max_position_qty is not None:
            qty = min(qty, strat_cfg.max_position_qty)

        result = place_order_market(client, intent, qty)
        journal.log_order(intent, result)
        if not result.success:
            raise HTTPException(status_code=502, detail=result.error or "Fallo al enviar orden a Bybit")
        state.mark_position_open(intent.symbol, intent.strategy, intent.side, result.qty or qty, intent.entry_price)
        return _format_result(result)

    if payload.action == "exit":
        position = state.get_position(intent.symbol, intent.strategy)
        if not position:
            return {"status": "no_position"}
        qty = position.qty
        result = place_order_market(client, intent, qty)
        journal.log_order(intent, result)
        if not result.success:
            raise HTTPException(status_code=502, detail=result.error or "Fallo al cerrar orden en Bybit")
        state.mark_position_closed(intent.symbol, intent.strategy)
        return _format_result(result)

    return {"status": "ignored"}


@router.get("/health")
async def healthcheck():
    return {"status": "ok", "open_positions": [pos.__dict__ for pos in state.get_open_positions()]}


def _format_result(result: OrderResult):
    if result.success:
        return {
            "status": "ok",
            "order_id": result.order_id,
            "filled_price": result.filled_price,
            "qty": result.qty,
        }
    logger.error("Fallo al ejecutar orden: %s", result.error)
    return {"status": "error", "detail": result.error}
