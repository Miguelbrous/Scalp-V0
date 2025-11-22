from __future__ import annotations

import logging
from typing import Optional

from pybit.unified_trading import HTTP

from .config import Settings, get_settings
from .models import OrderIntent, OrderResult

logger = logging.getLogger(__name__)


def get_client(settings: Optional[Settings] = None) -> HTTP:
    """Devuelve un cliente HTTP de Bybit listo para usar."""
    settings = settings or get_settings()
    client = HTTP(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet="testnet" in settings.bybit_base_url,
    )
    client.endpoint = settings.bybit_base_url.rstrip("/")
    return client


def _check_retcode(payload: dict) -> None:
    code = payload.get("retCode")
    if code not in (None, 0):
        message = payload.get("retMsg", "Error desconocido de Bybit")
        raise RuntimeError(f"Bybit error ({code}): {message}")


def _extract_usdt_balance(data: dict) -> float:
    result = data.get("result", {})
    for entry in result.get("list", []):
        for coin in entry.get("coin", []):
            if coin.get("coin") == "USDT":
                return float(coin.get("equity", 0.0))
    raise RuntimeError("La respuesta de Bybit no contiene balance USDT.")


def get_balance(client: HTTP) -> float:
    """Lee el balance disponible en USDT."""
    try:
        data = client.get_wallet_balance(accountType="UNIFIED")
        _check_retcode(data)
        return _extract_usdt_balance(data)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error al consultar balance: %s", exc)
        raise RuntimeError("No fue posible obtener el balance en USDT.") from exc


def place_order_market(client: HTTP, intent: OrderIntent, qty: float) -> OrderResult:
    """Crea una orden de mercado y configura SL/TP si aplica."""
    side = "Buy" if intent.side == "buy" else "Sell"
    try:
        order = client.place_order(
            category="linear",
            symbol=intent.symbol,
            side=side,
            orderType="Market",
            qty=str(round(qty, 6)),
            timeInForce="GTC",
            reduceOnly=False,
            closeOnTrigger=False,
            
            
        )
        try:
            _check_retcode(order)
        except RuntimeError as exc:  # Bybit devolvió error lógico
            return OrderResult(success=False, error=str(exc))
        result = order.get("result", {})
        return OrderResult(
            success=True,
            order_id=result.get("orderId"),
            filled_price=float(result.get("avgPrice") or intent.entry_price),
            qty=float(result.get("cumExecQty") or qty),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error al enviar orden: %s", exc)
        return OrderResult(success=False, error=str(exc))
