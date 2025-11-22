from __future__ import annotations

from functools import lru_cache
from typing import Dict, Literal, Optional

from pydantic import BaseModel, BaseSettings, Field, validator


class StrategyConfig(BaseModel):
    max_position_qty: Optional[float] = Field(None, gt=0.0, description='Limite superior de contratos/monedas')
    symbol: str
    risk_per_trade: Optional[float] = Field(
        None, ge=0.0, le=0.05, description="Anula el riesgo por defecto si se define."
    )
    sl_multiplier: float = Field(..., gt=0.0)
    tp_multiplier: float = Field(..., gt=0.0)
    max_concurrent_trades: int = Field(1, ge=1)
    order_type: Literal["market", "limit"] = "market"
    default_sl_distance_pct: float = Field(
        0.003,
        gt=0.0,
        description="Distancia relativa por defecto si TradingView no envía SL.",
    )
    default_tp_distance_pct: float = Field(0.006, gt=0.0)


class Settings(BaseSettings):
    bybit_api_key: str
    bybit_api_secret: str
    bybit_base_url: str = Field(
        "https://api-testnet.bybit.com",
        description="URL base (demo/mainnet).",
    )
    webhook_secret: str
    default_risk_per_trade: float = Field(0.0005, gt=0.0, le=0.05)
    strategies: Dict[str, StrategyConfig] = Field(default_factory=dict)

    @validator("strategies", pre=True, always=True)
    def _inject_default_strategies(cls, value: Optional[Dict[str, StrategyConfig]]):
        if value:
            return value
        return {
            "EMA_SHORT_SOL_1H": StrategyConfig(
                symbol="SOLUSDT",
                risk_per_trade=0.0005,
                sl_multiplier=1.5,
                tp_multiplier=2.0,
                max_concurrent_trades=1,
                max_position_qty=2.0,
            ),
            "OPEN_RANGE_SOL_15M": StrategyConfig(
                symbol="SOLUSDT",
                risk_per_trade=0.0005,
                sl_multiplier=1.2,
                tp_multiplier=1.8,
                max_concurrent_trades=1,
                default_sl_distance_pct=0.004,
                default_tp_distance_pct=0.008,
                max_position_qty=2.0,
            ),
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Carga memoizada de la configuración."""
    return Settings()


def get_strategy_config(name: str) -> StrategyConfig:
    settings = get_settings()
    try:
        return settings.strategies[name]
    except KeyError as exc:
        raise KeyError(f"Estrategia no configurada: {name}") from exc
