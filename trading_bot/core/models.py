from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, validator


class TradingViewPayload(BaseModel):
    secret: str
    symbol: str
    strategy: str
    side: Literal["long", "short"]
    action: Literal["entry", "exit"]
    price: float
    timestamp: str

    @validator("price")
    def _positive_price(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("El precio debe ser positivo.")
        return value


class OrderIntent(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "limit"] = "market"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_perc: float
    strategy: str

    @validator("stop_loss", "take_profit", "entry_price")
    def _positive_numbers(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Los precios deben ser positivos.")
        return value

    @validator("risk_perc")
    def _valid_risk(cls, value: float) -> float:
        if value <= 0 or value > 0.05:
            raise ValueError("El riesgo por operación debe estar entre 0 y 5 %.")
        return value


class OrderResult(BaseModel):
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    filled_price: Optional[float] = None
    qty: Optional[float] = None
