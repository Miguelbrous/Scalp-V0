from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from core.config_manager import BotConfig


class BybitClient:
    """Thin REST client for Bybit v5 private/public endpoints."""

    def __init__(self, config: BotConfig) -> None:
        load_dotenv()
        self._config = config
        self._base_url = config.environment.rest_url
        self._api_key = os.getenv("BYBIT_API_KEY")
        self._api_secret = os.getenv("BYBIT_API_SECRET")
        if not self._api_key or not self._api_secret:
            raise RuntimeError("API credentials missing. Set BYBIT_API_KEY and BYBIT_API_SECRET in .env")

    def create_order(
        self,
        *,
        side: str,
        qty: float,
        price: float | None,
        order_type: str = "Market",
        sl: float | None = None,
        tp: float | None = None,
        time_in_force: str = "GoodTillCancel",
    ) -> Dict[str, Any]:
        body = {
            "category": "linear",
            "symbol": self._config.symbol.name,
            "side": side,
            "orderType": order_type,
            "qty": str(qty),
            "timeInForce": time_in_force,
        }
        if price:
            body["price"] = str(price)
        if sl:
            body["stopLoss"] = str(sl)
        if tp:
            body["takeProfit"] = str(tp)
        return self._private_post("/v5/order/create", body)

    def amend_sl_tp(self, order_id: str, sl: float | None, tp: float | None) -> Dict[str, Any]:
        body = {
            "category": "linear",
            "symbol": self._config.symbol.name,
            "orderId": order_id,
        }
        if sl:
            body["stopLoss"] = str(sl)
        if tp:
            body["takeProfit"] = str(tp)
        return self._private_post("/v5/order/amend", body)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        body = {
            "category": "linear",
            "symbol": self._config.symbol.name,
            "orderId": order_id,
        }
        return self._private_post("/v5/order/cancel", body)

    def get_open_orders(self) -> Dict[str, Any]:
        params = {
            "category": "linear",
            "symbol": self._config.symbol.name,
        }
        return self._private_get("/v5/order/realtime", params)

    def get_position(self) -> Dict[str, Any]:
        params = {
            "category": "linear",
            "symbol": self._config.symbol.name,
        }
        return self._private_get("/v5/position/list", params)

    def get_executions(self, start_time: int | None = None, limit: int = 50) -> Dict[str, Any]:
        params = {
            "category": "linear",
            "symbol": self._config.symbol.name,
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        return self._private_get("/v5/execution/list", params)

    # ------------------------------------------------------------------
    def _private_post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._send_request("POST", path, body=body)

    def _private_get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._send_request("GET", path, params=params)

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        if body:
            body = {k: v for k, v in body.items() if v is not None}

        serialized_body = json.dumps(body) if body else ""
        if method.upper() == "GET" and params:
            serialized_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        else:
            serialized_params = ""
        sign_payload = timestamp + self._api_key + recv_window + (serialized_params or serialized_body)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }

        url = f"{self._base_url}{path}"
        resp = requests.request(method, url, params=params, data=serialized_body or None, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
