from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .models import OrderIntent, OrderResult, TradingViewPayload


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
SIGNALS_FILE = LOG_DIR / "signals.csv"
TRADES_FILE = LOG_DIR / "trades.csv"


def _write_row(file_path: Path, headers: list[str], row: list):
    file_exists = file_path.exists()
    with file_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_signal(payload: TradingViewPayload) -> None:
    headers = [
        "timestamp",
        "strategy",
        "symbol",
        "side",
        "action",
        "price",
        "raw_timestamp",
    ]
    row = [
        _now_iso(),
        payload.strategy,
        payload.symbol,
        payload.side,
        payload.action,
        payload.price,
        payload.timestamp,
    ]
    _write_row(SIGNALS_FILE, headers, row)


def log_order(intent: OrderIntent, result: OrderResult) -> None:
    headers = [
        "timestamp",
        "strategy",
        "symbol",
        "side",
        "type",
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_perc",
        "success",
        "order_id",
        "filled_price",
        "qty",
        "error",
    ]
    row = [
        _now_iso(),
        intent.strategy,
        intent.symbol,
        intent.side,
        intent.type,
        intent.entry_price,
        intent.stop_loss,
        intent.take_profit,
        intent.risk_perc,
        result.success,
        result.order_id or "",
        result.filled_price or "",
        result.qty or "",
        result.error or "",
    ]
    _write_row(TRADES_FILE, headers, row)
