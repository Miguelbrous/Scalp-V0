from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


class ConfigValidationError(RuntimeError):
    """Raised when the user provided configuration fails validation."""


@dataclass(frozen=True)
class EnvironmentConfig:
    name: str
    rest_url: str
    websocket_url: str


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_daily_trades: int
    max_consecutive_losses_for_cooldown: int
    min_account_balance_usdt: float


@dataclass(frozen=True)
class SymbolConfig:
    name: str
    leverage: int
    contract_type: str


@dataclass(frozen=True)
class RiskLimitsConfig:
    global_drawdown_pct: float
    limited_mode_recovery_pct: float
    limited_mode_duration_minutes: int
    cooldown_short_minutes: int
    cooldown_long_minutes: int
    reference_account_size_usdt: float


@dataclass(frozen=True)
class StrategyParams:
    ema_fast: int
    ema_slow: int
    vwap_window: int
    atr_period: int
    atr_multiplier_sl: float
    atr_multiplier_tp: float
    min_atr: float
    time_stop_minutes: int
    max_vwap_distance_pct: float
    max_price_ema_distance_pct: float
    pullback_tolerance_pct: float
    min_volatility: float
    rsi_period: int
    rsi_long_max: float
    rsi_long_min: float
    rsi_short_max: float
    rsi_short_min: float


@dataclass(frozen=True)
class SessionsConfig:
    preferred: List[Dict[str, str]]
    allow_offsession_trades_if_high_quality: bool


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    runtime_dir: str


@dataclass(frozen=True)
class PromotionRules:
    min_demo_trades: int
    min_net_profit_usdt: float
    max_drawdown_pct: float


@dataclass(frozen=True)
class BotConfig:
    environment: EnvironmentConfig
    profile: ProfileConfig
    symbol: SymbolConfig
    risk_limits: RiskLimitsConfig
    strategy_params: StrategyParams
    sessions: SessionsConfig
    logging: LoggingConfig
    promotion_rules: PromotionRules

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary representation of the configuration."""
        return {
            "environment": self.environment.__dict__,
            "profile": self.profile.__dict__,
            "symbol": self.symbol.__dict__,
            "risk_limits": self.risk_limits.__dict__,
            "strategy_params": self.strategy_params.__dict__,
            "sessions": {
                "preferred": self.sessions.preferred,
                "allow_offsession_trades_if_high_quality": self.sessions.allow_offsession_trades_if_high_quality,
            },
            "logging": self.logging.__dict__,
            "promotion_rules": self.promotion_rules.__dict__,
        }


class ConfigManager:
    """Load and validate configuration from config/config.json."""

    def __init__(self, config_path: str | Path = "config/config.json") -> None:
        self._config_path = Path(config_path)
        self._config: BotConfig | None = None

    @property
    def config(self) -> BotConfig:
        if self._config is None:
            self._config = self._load_and_validate()
        return self._config

    def reload(self) -> BotConfig:
        """Force reloading configuration from the file system."""
        self._config = self._load_and_validate()
        return self._config

    # Internal helpers -------------------------------------------------
    def _load_and_validate(self) -> BotConfig:
        if not self._config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as fp:
            raw_config = json.load(fp)

        self._validate_basic(raw_config)
        return self._parse(raw_config)

    @staticmethod
    def _parse(raw: Dict[str, Any]) -> BotConfig:
        environment = EnvironmentConfig(**raw["environment"])
        profile = ProfileConfig(**raw["profile"])
        symbol = SymbolConfig(**raw["symbol"])
        risk_limits = RiskLimitsConfig(**raw["risk_limits"])
        strategy_params = StrategyParams(**raw["strategy_params"])
        sessions = SessionsConfig(**raw["sessions"])
        logging_cfg = LoggingConfig(**raw["logging"])
        promotion_rules = PromotionRules(**raw["promotion_rules"])

        return BotConfig(
            environment=environment,
            profile=profile,
            symbol=symbol,
            risk_limits=risk_limits,
            strategy_params=strategy_params,
            sessions=sessions,
            logging=logging_cfg,
            promotion_rules=promotion_rules,
        )

    @staticmethod
    def _validate_basic(raw: Dict[str, Any]) -> None:
        """Perform lightweight validation to catch obvious configuration mistakes."""
        required_sections = [
            "environment",
            "profile",
            "symbol",
            "risk_limits",
            "strategy_params",
            "sessions",
            "logging",
            "promotion_rules",
        ]
        missing = [sec for sec in required_sections if sec not in raw]
        if missing:
            raise ConfigValidationError(f"Missing sections in config: {', '.join(missing)}")

        env_name = raw["environment"].get("name")
        if env_name not in {"ENV_DEMO_MAINNET", "ENV_LIVE_MAINNET"}:
            raise ConfigValidationError("Environment name must be ENV_DEMO_MAINNET or ENV_LIVE_MAINNET")

        profile_name = raw["profile"].get("name")
        if profile_name not in {"PROFILE_PROD", "PROFILE_EXPLORER"}:
            raise ConfigValidationError("Profile name must be PROFILE_PROD or PROFILE_EXPLORER")

        ConfigManager._validate_percentage(raw["profile"].get("risk_per_trade_pct"), "risk_per_trade_pct", 0.10)
        ConfigManager._validate_percentage(raw["profile"].get("max_daily_loss_pct"), "max_daily_loss_pct", 0.2)

        if raw["profile"].get("max_daily_trades", 0) <= 0:
            raise ConfigValidationError("max_daily_trades must be positive")

        max_losses = raw["profile"].get("max_consecutive_losses_for_cooldown", 0)
        if max_losses <= 0:
            raise ConfigValidationError("max_consecutive_losses_for_cooldown must be positive")

        if raw["risk_limits"].get("global_drawdown_pct", 0) <= 0:
            raise ConfigValidationError("global_drawdown_pct must be positive")

        ema_fast = raw["strategy_params"].get("ema_fast", 0)
        ema_slow = raw["strategy_params"].get("ema_slow", 0)
        if not (1 <= ema_fast < ema_slow):
            raise ConfigValidationError("ema_fast must be >=1 and strictly lower than ema_slow")

        if raw["strategy_params"].get("atr_period", 0) < 5:
            raise ConfigValidationError("atr_period must be >=5")

        min_atr = raw["strategy_params"].get("min_atr")
        if min_atr is None or min_atr <= 0:
            raise ConfigValidationError("min_atr must be > 0")

        if raw["strategy_params"].get("max_vwap_distance_pct", 0) <= 0:
            raise ConfigValidationError("max_vwap_distance_pct must be > 0")

        if raw["strategy_params"].get("max_price_ema_distance_pct", 0) <= 0:
            raise ConfigValidationError("max_price_ema_distance_pct must be > 0")

        if raw["strategy_params"].get("pullback_tolerance_pct", 0) <= 0:
            raise ConfigValidationError("pullback_tolerance_pct must be > 0")

        if raw["strategy_params"].get("min_volatility", 0) < 0:
            raise ConfigValidationError("min_volatility must be >= 0")

        rsi_period = raw["strategy_params"].get("rsi_period", 0)
        if rsi_period < 5:
            raise ConfigValidationError("rsi_period must be >= 5")

        if raw["strategy_params"].get("rsi_long_max", 0) <= 0:
            raise ConfigValidationError("rsi_long_max must be > 0")

        if raw["strategy_params"].get("rsi_long_min", 0) <= 0:
            raise ConfigValidationError("rsi_long_min must be > 0")

        if raw["strategy_params"]["rsi_long_min"] >= raw["strategy_params"]["rsi_long_max"]:
            raise ConfigValidationError("rsi_long_min must be lower than rsi_long_max")

        if raw["strategy_params"].get("rsi_short_max", 0) <= 0:
            raise ConfigValidationError("rsi_short_max must be > 0")

        if raw["strategy_params"].get("rsi_short_min", 0) <= 0:
            raise ConfigValidationError("rsi_short_min must be > 0")

        if raw["strategy_params"]["rsi_short_min"] >= raw["strategy_params"]["rsi_short_max"]:
            raise ConfigValidationError("rsi_short_min must be lower than rsi_short_max")

    @staticmethod
    def _validate_percentage(value: Any, field_name: str, max_allowed: float) -> None:
        if value is None:
            raise ConfigValidationError(f"{field_name} must be provided")
        if not 0 < float(value) <= max_allowed:
            raise ConfigValidationError(f"{field_name} must be between 0 and {max_allowed}")
