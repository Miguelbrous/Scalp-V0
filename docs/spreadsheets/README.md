# Guía para rellenar las plantillas de Excel

Estas dos hojas sirven como diario manual complementario del bot. Ambas se encuentran en `docs/spreadsheets/` y el bot las actualiza automáticamente cada vez que se registra un trade (ver `analytics/excel_sync.py`). Aun así, puedes editar manualmente cualquier campo si necesitas observaciones adicionales.

## 1. `12. Interes compuesto.xlsx`

Hoja enfocada en el seguimiento diario/semanal de sesiones.

### Campos principales
- **Capital**: usa `risk_limits.reference_account_size_usdt` o tu balance real al empezar la semana.
- **% Riesgo**: copia `profile.risk_per_trade_pct` (ej. `0.005` = 0.5 %) o el valor real aplicado ese día.
- **$ Operar**: resultado de `RiskManager` (`risk_amount`); puedes obtenerlo del log de cada trade (`logs/trades/trades.csv` columna `r_multiple * risk_amount`).
- **# StopLoss / # TakeProfit**: cuenta de trades cerrados por SL/TP en la sesión. Puedes filtrarlo leyendo la columna `mode` + `description` del CHANGELOG o directamente del `TradeRecord` (si `pnl < 0` y se cerró por SL).
- **StopLoss (=) / TakeProfit**: son los multiplicadores que ya aparecen en la fila 3. Déjalos como referencia (0.05 = 5 %) o cambia si el perfil varía.
- **PNL**: suma de `pnl` de los trades del día (ver `logs/trades/trades.csv`). Puedes copiarlo también del CHANGELOG (cada trade se registra con su `pnl`).

### Cómo rellenar una semana
1. Resetea las filas 4–10 con la semana actual (día 1…7).
2. Cada día:
   - Capital = saldo inicial de la jornada (consulta `state_manager.export_state()['equity_stats']['cumulative_pnl']` + referencia).
   - % Riesgo = `profile.risk_per_trade_pct`.
   - `$ Operar` = `RiskManager.evaluate(...).risk_amount`.
   - `# StopLoss`/`# Take Profit` = contador según `TradeRecord`.
   - `PNL` = suma diaria del CSV.
3. Al cerrar la semana, usa la sección “Este es tu rendimiento de la sesión del día” para apuntar el % ganado/perdido (PNL / capital inicial de la semana).

## 2. `26. Plan de inversion.xlsx`

Plan de capital compuesto a largo plazo.

### Campos amarillos editables
- **Nombre / Fecha de inicio**: libre.
- **Saldo inicial**: mismo valor que `risk_limits.reference_account_size_usdt` o tu balance real.
- **Profit diario Plan (% y absoluto)**: puedes copiar el target diario configurado (ej. 0.05 = 5 %). Ajusta “Profit diario Plan” si decides otro objetivo.
- **Depositos y retiros**: registra cualquier movimiento externo.
- **Saldo real**: balance actual real (consulta la cuenta demo/live).
- **Profit ganado / Cumplimiento**: saca el P&L real diario del CSV de trades.

### Cómo actualizar cada día
1. En la fila con la fecha del día (`fechas`):
   - `Saldo Inicial del plan`: saldo de apertura (día anterior `Saldo AL FINAL DEL DÍA`).
   - `Saldo ajustado teórico`: lo deja la fórmula (saldo anterior * (1 + profit plan)).
   - `Saldo real`: balance real tras cerrar la sesión.
   - `saldo a cerrar`: objetivo (saldo inicial + profit plan).
   - `Saldo AL FINAL DEL DÍA`: rellena manualmente con el saldo real tras operaciones.
   - `mínimo a ganar` / `Min. ganar real`: objetivo en USD vs. lo que realmente obtuviste (usa P&L real).
   - `Profit ganado`: P&L real del día.
   - `Cumplimiento`: marca 1 si el día alcanzó el mínimo, 0 si no.
   - `Trade realizados / Trades Efectivos`: toma las métricas desde `trade_logger` (total de trades y cuántos positivos). `% efectivos` = winrate diario.
2. `Profit Acumulado` (en la parte superior) se puede actualizar sumando los P&L reales, o leyendo el total del CSV.

## Cómo obtener los datos del bot

- **Trades individuales**: `logs/trades/trades.csv` (campos `timestamp`, `side`, `qty`, `entry_price`, `exit_price`, `pnl`, `r_multiple`).
- **Estadísticas**: `analytics/stats_engine.py` puede invocarse desde un shell Python para recalcular winrate, DD, etc.
- **Modo actual / P&L acumulado**: usa `core/state_manager.StateManager.export_state()` o revisa `logs/runtime/scalp_v0.log`.
- **Changelog**: `docs/CHANGELOG.md` tiene cada trade y transición con `pnl` para referencia rápida.

Con estos datos puedes alimentar manualmente ambos Excel después de cada sesión o automatizarlo en futuras versiones.

## Actualización automática

Desde Scalp V0 el módulo `analytics/excel_sync.py`:

- Lee `logs/trades/trades.csv` tras cada trade.
- Calcula PnL y winrate diario.
- Escribe los valores en:
  - `12. Interes compuesto.xlsx`: columna Día, Capital, % riesgo, monto por operación, #SL/#TP y PnL.
  - `26. Plan de inversion.xlsx`: fecha calendario, capital teórico y real, PnL diario, cumplimiento, total de trades y winrate.

Si el archivo está abierto y no puede modificarse, el bot mostrará una advertencia en consola pero seguirá operando.
