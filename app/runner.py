from __future__ import annotations

# ================================================================
# Scalp V0 - MOTOR CONGELADO
# ---------------------------------------------------------------
# Este archivo forma parte del nucleo operativo de Scalp V0.
# No modificar la logica de trading ni riesgo aqui salvo para
# corregir bugs criticos autorizados por el usuario.
# Las estrategias nuevas se prototipan en TradingView y solo se
# portan a Python cuando cumplen PF > 1.3, 200+ trades y DD < 20 %.
# ================================================================

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Añadir la carpeta raíz del proyecto (Scalp V0) al sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from analytics.excel_sync import ExcelSync
from analytics.promotion_checker import PromotionChecker
from analytics.stats_engine import StatsEngine
from analytics.trade_logger import TradeLogger, TradeRecord
from core import persistence
from core.config_manager import ConfigManager
from core.doc_writer import append_changelog, update_capabilities
from core.state_manager import BotMode, StateManager, TradeResult
from data.market_data import MarketDataClient
from data.symbol_info import get_symbol_info
from execution.bybit_client import BybitClient
from execution.order_executor import ActiveTrade, OrderExecutor
from risk.limits_checker import LimitsChecker
from risk.risk_manager import RiskManager, RiskResult
from strategy.scalp_v0 import ScalpV0Strategy

logger = logging.getLogger("Scalp_V0")


class BotRunner:
    """Glue layer binding together configuration, data, strategy, and execution."""

    def __init__(self) -> None:
        self._config = ConfigManager().config
        setup_logging(self._config.logging.level, self._config.logging.runtime_dir)

        initial_state = persistence.load_state()
        self._state_manager = StateManager(self._config, initial_state=initial_state)
        self._last_mode = self._state_manager.current_mode()
        append_changelog(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "ADD",
                "module": "app/runner",
                "description": f"Bot iniciado con {self._config.environment.name} / {self._config.profile.name}",
                "version": self._state_manager.bump_internal_version(),
            }
        )

        self._symbol_info = get_symbol_info(self._config.symbol.name)
        self._market_data = MarketDataClient(self._config)
        self._strategy = ScalpV0Strategy(self._config)
        self._risk_manager = RiskManager(self._config, self._symbol_info)
        self._bybit_client = BybitClient(self._config)
        self._order_executor = OrderExecutor(self._bybit_client)
        self._order_executor.bootstrap_open_position()
        self._trade_logger = TradeLogger()
        self._stats_engine = StatsEngine(self._trade_logger)
        self._promotion_checker = PromotionChecker(self._config, self._stats_engine)
        self._limits_checker = LimitsChecker(self._config, self._state_manager)
        self._excel_sync = ExcelSync(self._config)

        self._cycle_counter = 0
        self._update_capabilities_doc()

    def run(self) -> None:
        logger.info("Starting Scalp_V0 runner with env %s / profile %s", self._config.environment.name, self._config.profile.name)
        while True:
            try:
                self._cycle()
            except Exception as exc:  # pragma: no cover - main loop defence
                logger.exception("Unhandled exception during cycle: %s", exc)
                time.sleep(10)

    def _cycle(self) -> None:
        snapshot = self._market_data.refresh_snapshot()
        signal = self._strategy.generate_signal(snapshot)
        if signal.side == "NO_TRADE":
            if signal.reason:
                logger.info("NO_TRADE en estrategia: %s", signal.reason)
            else:
                logger.info("NO_TRADE: revisar logs de strategy.scalp_v0 para detalles")
            time.sleep(5)
            self._post_cycle_housekeeping()
            return

        limit = self._limits_checker.evaluate(snapshot)
        if not limit.allow_trade:
            message = f"Trade blocked by limits: {limit.reason}"
            if limit.reason == "COOLDOWN":
                cooldown_type, minutes = self._state_manager.current_cooldown_countdown()
                message += f" (tipo={cooldown_type or 'N/A'}, quedan {minutes:.1f} min)"
            logger.info(message)
            time.sleep(5)
            self._post_cycle_housekeeping()
            return

        risk = self._risk_manager.evaluate(
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            tp_price=signal.tp_price,
        )
        active_trade = self._order_executor.open_trade(
            side=signal.side,
            qty=risk.qty,
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            tp_price=signal.tp_price,
            time_stop_minutes=signal.time_stop_minutes,
        )
        logger.info("Opened trade %s qty=%s entry=%.2f", signal.side, risk.qty, signal.entry_price)

        self._monitor_trade(active_trade, risk)
        self._post_cycle_housekeeping()

    def _monitor_trade(self, trade: ActiveTrade, risk: RiskResult) -> None:
        """Simple polling loop waiting for the trade to close."""
        while True:
            time.sleep(10)
            snapshot = self._market_data.refresh_snapshot()
            now = datetime.now(timezone.utc)

            exit_price = self._order_executor.poll_trade_close(trade)
            if exit_price is not None:
                self._finalize_trade(trade, exit_price, risk, reason="SL/TP")
                break

            if trade.is_time_stop_reached(now):
                exit_price = self._order_executor.close_trade(reason="TIME_STOP") or snapshot.price
                self._finalize_trade(trade, exit_price, risk, reason="TIME_STOP")
                break

    def _finalize_trade(self, trade: ActiveTrade, exit_price: float, risk: RiskResult, reason: str) -> None:
        pnl = self._calculate_pnl(trade, exit_price)
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Trade closed (%s) pnl=%.2f", reason, pnl)
        trade_record = TradeRecord(
            timestamp=timestamp,
            environment=self._config.environment.name,
            profile=self._config.profile.name,
            mode=self._state_manager.current_mode().value,
            side=trade.side,
            qty=trade.qty,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            sl=trade.sl_price,
            tp=trade.tp_price,
            pnl=pnl,
            fees=0.0,
            r_multiple=pnl / risk.risk_amount if risk.risk_amount else 0.0,
        )
        self._trade_logger.log_trade(trade_record)
        trade_result = TradeResult(
            pnl=pnl,
            timestamp=datetime.now(timezone.utc),
        )
        self._state_manager.on_trade_closed(trade_result)
        self._excel_sync.update_all()
        append_changelog(
            {
                "timestamp": timestamp,
                "type": "UPDATE",
                "module": "execution/order_executor",
                "description": f"Trade {trade.side} cerrado por {reason} con pnl {pnl:.2f}",
                "version": self._state_manager.bump_internal_version(),
            }
        )
        counters = self._state_manager.cooldown_counters
        logger.info(
            "Transiciones cooldown - corto:%s largo:%s",
            counters.get("short", 0),
            counters.get("long", 0),
        )

    def _calculate_pnl(self, trade: ActiveTrade, exit_price: float) -> float:
        delta = exit_price - trade.entry_price
        if trade.side == "SHORT":
            delta = -delta
        return delta * trade.qty

    def _post_cycle_housekeeping(self) -> None:
        self._cycle_counter += 1
        self._check_mode_transition()
        if self._cycle_counter % 5 == 0:
            persistence.save_state(self._state_manager)
        if self._cycle_counter % 60 == 0:
            stats = self._stats_engine.compute()
            promo = self._promotion_checker.evaluate()
            logger.info(
                "Stats updated: trades=%s winrate=%.2f%% netPnL=%.2f promo_ready=%s",
                stats.total_trades,
                stats.winrate * 100,
                stats.net_pnl,
                promo.demo_to_live_ready,
            )
        if self._state_manager.current_mode() == BotMode.COOLDOWN:
            cooldown_type, minutes = self._state_manager.current_cooldown_countdown()
            logger.info(
                "En COOLDOWN (%s). Tiempo restante aproximado: %.1f min",
                cooldown_type or "desconocido",
                minutes,
            )

    def _check_mode_transition(self) -> None:
        current = self._state_manager.current_mode()
        if current != self._last_mode:
            append_changelog(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "UPDATE",
                    "module": "core/state_manager",
                    "description": f"Transición de modo a {current.value}",
                    "version": self._state_manager.bump_internal_version(),
                }
            )
            counters = self._state_manager.cooldown_counters
            logger.info(
                "Modo actual: %s | Cooldowns disparados -> corto:%s largo:%s",
                current.value,
                counters.get("short", 0),
                counters.get("long", 0),
            )
            self._last_mode = current

    def _update_capabilities_doc(self) -> None:
        update_capabilities(
            {
                "datos_mercado": ["Velas 1m/5m/15m", "EMA/VWAP/ATR calculados"],
                "estrategia": ["Pullbacks 1m", "Tendencia EMA20/EMA50", "Filtro ATR"],
                "riesgo": ["Perfiles PROD/EXPLORER", "% riesgo", "Límite diario"],
                "estados": ["NORMAL", "COOLDOWN", "LIMITED", "HALT"],
                "ejecucion": ["SL/TP inicial", "fills reales /v5/execution/list"],
                "stats": ["winrate", "R medio", "DD máximo"],
            }
        )


def setup_logging(level: str, runtime_dir: str) -> None:
    Path(runtime_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(runtime_dir) / "scalp_v0.log"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    runner = BotRunner()
    runner.run()


if __name__ == "__main__":
    main()
