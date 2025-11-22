from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd
import requests

from core.config_manager import BotConfig

log = logging.getLogger(__name__)


@dataclass
class CandleSnapshot:
    open: float
    high: float
    low: float
    close: float
    ema_fast: float


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    trend_5m: str
    trend_15m: str
    ema_fast: float
    ema_slow: float
    atr: float
    vwap: float
    vwap_distance_pct: float
    volatility: float
    rsi: float | None
    current_candle: CandleSnapshot
    previous_candle: CandleSnapshot | None
    timestamp: datetime


class MarketDataClient:
    """Pulls lightweight market data from Bybit for indicator calculations."""

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._rest_url = config.environment.rest_url
        self._symbol = config.symbol.name
        self._strategy = config.strategy_params
        self._latest_snapshot: Optional[MarketSnapshot] = None

    def refresh_snapshot(self) -> MarketSnapshot:
        """Fetch the latest candles for multiple timeframes and compute indicators."""
        intervals = {"1": 200, "5": 200, "15": 200}
        candles: Dict[str, pd.DataFrame] = {}
        for interval, limit in intervals.items():
            try:
                candles[interval] = self._fetch_klines(interval=interval, limit=limit)
            except Exception as exc:  # pragma: no cover - defensive logging
                log.warning("Failed to fetch %sm data: %s", interval, exc)
                raise

        snapshot = self._build_snapshot(candles)
        self._latest_snapshot = snapshot
        return snapshot

    def get_latest_market_snapshot(self) -> Optional[MarketSnapshot]:
        if self._latest_snapshot is None:
            return self.refresh_snapshot()
        return self._latest_snapshot

    # ------------------------------------------------------------------
    def _fetch_klines(self, interval: str, limit: int = 200) -> pd.DataFrame:
        params = {
            "category": "linear",
            "symbol": self._symbol,
            "interval": interval,
            "limit": limit,
        }
        url = f"{self._rest_url}/v5/market/kline"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("result", {}).get("list", [])

        records = [
            {
                "timestamp": datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
            for item in rows
        ]
        df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
        return df

    def _build_snapshot(self, candles: Dict[str, pd.DataFrame]) -> MarketSnapshot:
        one_min = candles["1"].copy()
        fast = self._strategy.ema_fast
        slow = self._strategy.ema_slow
        one_min["ema_fast"] = one_min["close"].ewm(span=fast, adjust=False).mean()
        one_min["ema_slow"] = one_min["close"].ewm(span=slow, adjust=False).mean()
        atr_df = self._compute_atr(one_min, period=self._strategy.atr_period)
        one_min["atr"] = atr_df["atr"]
        one_min["vwap"] = self._compute_vwap(one_min)
        one_min["rsi"] = self._compute_rsi(one_min["close"], period=self._strategy.rsi_period)

        latest = one_min.iloc[-1]
        prev_row = one_min.iloc[-2] if len(one_min) > 1 else None
        price = float(latest["close"])
        ema_fast_val = float(latest["ema_fast"])
        ema_slow_val = float(latest["ema_slow"])
        atr_val = float(latest["atr"])
        vwap_val = float(latest["vwap"])
        vwap_distance = (price - vwap_val) / vwap_val if vwap_val else 0.0
        rsi_val = float(latest["rsi"]) if "rsi" in latest and pd.notna(latest["rsi"]) else None

        current_candle = CandleSnapshot(
            open=float(latest["open"]),
            high=float(latest["high"]),
            low=float(latest["low"]),
            close=price,
            ema_fast=ema_fast_val,
        )
        previous_candle = None
        if prev_row is not None:
            previous_candle = CandleSnapshot(
                open=float(prev_row["open"]),
                high=float(prev_row["high"]),
                low=float(prev_row["low"]),
                close=float(prev_row["close"]),
                ema_fast=float(prev_row["ema_fast"]),
            )

        trend_5m = self._assess_trend(candles["5"])
        trend_15m = self._assess_trend(candles["15"])

        volatility = float(one_min["close"].pct_change().rolling(30).std().iloc[-1]) if len(one_min) >= 30 else 0.0

        return MarketSnapshot(
            symbol=self._symbol,
            price=price,
            trend_5m=trend_5m,
            trend_15m=trend_15m,
            ema_fast=ema_fast_val,
            ema_slow=ema_slow_val,
            atr=atr_val,
            vwap=vwap_val,
            vwap_distance_pct=vwap_distance * 100,
            volatility=volatility,
            rsi=rsi_val,
            current_candle=current_candle,
            previous_candle=previous_candle,
            timestamp=latest["timestamp"],
        )

    def _compute_atr(self, df: pd.DataFrame, period: int) -> pd.DataFrame:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return pd.DataFrame({"atr": atr})

    def _compute_vwap(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cumulative_vol = df["volume"].cumsum()
        cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
        return cumulative_tp_vol / cumulative_vol

    def _compute_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _assess_trend(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "UNKNOWN"
        ema_fast = df["close"].ewm(span=self._strategy.ema_fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self._strategy.ema_slow, adjust=False).mean()
        slope = ema_fast.iloc[-1] - ema_fast.iloc[-5] if len(ema_fast) > 5 else 0
        if ema_fast.iloc[-1] > ema_slow.iloc[-1] and slope > 0:
            return "BULLISH"
        if ema_fast.iloc[-1] < ema_slow.iloc[-1] and slope < 0:
            return "BEARISH"
        return "SIDEWAYS"
