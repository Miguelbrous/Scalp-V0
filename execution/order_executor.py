from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .bybit_client import BybitClient


@dataclass
class ActiveTrade:
    side: str
    qty: float
    entry_price: float
    sl_price: float
    tp_price: float
    opened_at: datetime
    entry_order_id: str
    time_stop_minutes: int
    entry_exec_time_ms: int
    last_exec_time_ms: int

    def is_time_stop_reached(self, now: datetime) -> bool:
        if self.time_stop_minutes <= 0:
            return False
        limit = self.opened_at + timedelta(minutes=self.time_stop_minutes)
        return now >= limit


class OrderExecutor:
    """Coordinates order placement and recovery using the Bybit client."""

    def __init__(self, client: BybitClient) -> None:
        self._client = client
        self._active_trade: Optional[ActiveTrade] = None

    def bootstrap_open_position(self) -> Optional[ActiveTrade]:
        """Recover information about any open position (best-effort)."""
        return self.refresh_active_trade()

    def open_trade(
        self,
        *,
        side: str,
        qty: float,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        time_stop_minutes: int,
    ) -> ActiveTrade:
        """Place a new order and set SL/TP together whenever possible."""
        resp = self._client.create_order(
            side="Buy" if side == "LONG" else "Sell",
            qty=qty,
            price=None,
            order_type="Market",
            sl=sl_price,
            tp=tp_price,
        )
        order_id = resp.get("result", {}).get("orderId", "unknown")
        fill_price, exec_time = self._fetch_fill(order_id)
        entry_price = fill_price or entry_price
        exec_time_ms = exec_time or int(time.time() * 1000)
        trade = ActiveTrade(
            side=side,
            qty=qty,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            opened_at=datetime.now(timezone.utc),
            entry_order_id=order_id,
            time_stop_minutes=time_stop_minutes,
            entry_exec_time_ms=exec_time_ms,
            last_exec_time_ms=exec_time_ms,
        )
        self._active_trade = trade
        return trade

    def close_trade(self, *, reason: str, price: float | None = None) -> Optional[float]:
        """Close existing trade by market order."""
        if not self._active_trade:
            return None
        closing_side = "Sell" if self._active_trade.side == "LONG" else "Buy"
        resp = self._client.create_order(
            side=closing_side,
            qty=self._active_trade.qty,
            price=price,
            order_type="Market",
        )
        order_id = resp.get("result", {}).get("orderId", "unknown")
        fill_price, exec_time = self._fetch_fill(order_id)
        if exec_time and self._active_trade:
            self._active_trade.last_exec_time_ms = exec_time
        self._active_trade = None
        return fill_price

    def active_trade(self) -> Optional[ActiveTrade]:
        return self._active_trade

    def refresh_active_trade(self) -> Optional[ActiveTrade]:
        """Fetch real-time position info to keep local cache in sync."""
        position_info = self._client.get_position()
        rows = position_info.get("result", {}).get("list", [])
        for row in rows:
            size = float(row.get("size", 0))
            if size == 0:
                continue
            side = row.get("side", "Buy").upper()
            sl = float(row.get("stopLoss", 0) or 0)
            tp = float(row.get("takeProfit", 0) or 0)
            entry = float(row.get("entryPrice", 0))
            now_ms = int(time.time() * 1000)
            self._active_trade = ActiveTrade(
                side="LONG" if side == "BUY" else "SHORT",
                qty=size,
                entry_price=entry,
                sl_price=sl,
                tp_price=tp,
                opened_at=datetime.now(timezone.utc),
                entry_order_id=str(row.get("positionIdx", "unknown")),
                time_stop_minutes=self._active_trade.time_stop_minutes if self._active_trade else 0,
                entry_exec_time_ms=now_ms,
                last_exec_time_ms=now_ms,
            )
            return self._active_trade
        self._active_trade = None
        return None

    def poll_trade_close(self, trade: ActiveTrade) -> Optional[float]:
        """Check whether the trade has been closed by SL/TP and fetch actual exit price."""
        position_info = self._client.get_position()
        rows = position_info.get("result", {}).get("list", [])
        open_size = sum(float(row.get("size", 0)) for row in rows)
        if open_size > 0:
            return None
        exit_price = self._find_exit_fill(trade)
        self._active_trade = None
        return exit_price

    # ------------------------------------------------------------------
    def _fetch_fill(self, order_id: str) -> tuple[Optional[float], Optional[int]]:
        """Poll the executions endpoint to obtain the actual fill price/time."""
        for _ in range(5):
            time.sleep(1)
            resp = self._client.get_executions()
            executions = resp.get("result", {}).get("list", [])
            for row in executions:
                if row.get("orderId") == order_id:
                    price = float(row.get("execPrice", 0))
                    exec_time = int(row.get("execTime", 0))
                    return price, exec_time
        return None, None

    def _find_exit_fill(self, trade: ActiveTrade) -> Optional[float]:
        resp = self._client.get_executions(start_time=trade.entry_exec_time_ms)
        executions = resp.get("result", {}).get("list", [])
        if not executions:
            return None
        sorted_execs = sorted(executions, key=lambda row: int(row.get("execTime", 0)))
        for row in sorted_execs:
            exec_time = int(row.get("execTime", 0))
            if exec_time <= trade.last_exec_time_ms:
                continue
            side = row.get("side", "").upper()
            if trade.side == "LONG" and side == "SELL":
                trade.last_exec_time_ms = exec_time
                return float(row.get("execPrice", 0))
            if trade.side == "SHORT" and side == "BUY":
                trade.last_exec_time_ms = exec_time
                return float(row.get("execPrice", 0))
        return None
