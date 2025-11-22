# Strategy Lab Rules

## Estado actual: Scalp V0 congelado
- El bot operativo se llama **Scalp V0** y su motor queda congelado.
- No se debe reescribir `app/runner.py`, `core/state_manager.py`, `risk/risk_manager.py` ni `execution/*` salvo para corregir bugs críticos.
- El único símbolo en producción es **SOLUSDT** con apalancamiento 3 y contrato linear perpetual.
- Cualquier cambio a `config/config.json` o `data/symbol_info.py` debe respetar lo anterior y ser puramente correctivo.

## Reglas generales del laboratorio
- Toda estrategia nueva se desarrolla primero en TradingView (Pine Script) bajo `docs/tradingview/`.
- El bot en Python no se toca hasta que el usuario lo solicite con una frase explícita tipo: *"Esta estrategia en Pine tiene profit factor > 1.3, portala al bot."*
- Activo principal para pruebas: **SOLUSDT** en marcos recomendados 15m y 1h.
- No portar estrategias al bot hasta cumplir todos los criterios mínimos:
  1. **Profit factor > 1.3** en backtest.
  2. **200 o más trades cerrados**.
  3. **Drawdown máximo < 20 %** en el periodo evaluado.

## Flujo de trabajo del laboratorio
1. Diseñar la idea y documentar sus supuestos.
2. Crear un script Pine `docs/tradingview/<nombre>_experiment.pine` con panel de estadísticas (total trades, winrate, profit factor, PnL%).
3. Ejecutar backtests largos (mínimo varios meses) ajustando parámetros según corresponda.
4. Si la estrategia no alcanza los criterios → marcarla como **DESCARTADA** y no tocar el bot.
5. Si los criterios se cumplen → el usuario decidirá si pasa a fase candidata y solicita el porte a Python.

## Convenciones de nombres
- `*_experiment.pine`: Prototipos y pruebas iniciales. No deben integrarse a Scalp V0.
- `*_candidate.pine`: Estrategias que ya cumplen PF > 1.3, 200+ trades y DD aceptable; son candidatas a portarse cuando el usuario lo solicite.

## Recordatorio
- Correcciones de bugs en el bot están permitidas.
- Mejoras o cambios funcionales en estrategia, riesgo o ejecución solo se realizarán cuando exista una estrategia validada en Pine y el usuario confirme el inicio de Scalp V1.
