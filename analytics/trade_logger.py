from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class TradeRecord:
    timestamp: str
    environment: str
    profile: str
    mode: str
    side: str
    qty: float
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    pnl: float
    fees: float
    r_multiple: float


class TradeLogger:
    """Persist trades to CSV so that analytics modules can consume them later."""

    def __init__(self, trades_dir: str | Path = "logs/trades") -> None:
        self._dir = Path(trades_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "trades.csv"
        if not self._file.exists():
            self._write_header()

    def log_trade(self, record: TradeRecord) -> None:
        with self._file.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=self._fieldnames)
            writer.writerow(asdict(record))

    def read_all(self) -> List[TradeRecord]:
        if not self._file.exists():
            return []
        with self._file.open("r", newline="", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            return [
                TradeRecord(
                    timestamp=row["timestamp"],
                    environment=row["environment"],
                    profile=row["profile"],
                    mode=row["mode"],
                    side=row["side"],
                    qty=float(row["qty"]),
                    entry_price=float(row["entry_price"]),
                    exit_price=float(row["exit_price"]),
                    sl=float(row["sl"]),
                    tp=float(row["tp"]),
                    pnl=float(row["pnl"]),
                    fees=float(row["fees"]),
                    r_multiple=float(row["r_multiple"]),
                )
                for row in reader
            ]

    # ------------------------------------------------------------------
    @property
    def _fieldnames(self) -> Iterable[str]:
        return [
            "timestamp",
            "environment",
            "profile",
            "mode",
            "side",
            "qty",
            "entry_price",
            "exit_price",
            "sl",
            "tp",
            "pnl",
            "fees",
            "r_multiple",
        ]

    def _write_header(self) -> None:
        with self._file.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=self._fieldnames)
            writer.writeheader()

