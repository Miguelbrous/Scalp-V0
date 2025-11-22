# Project Roadmap

## V0 – Estado actual
- Motor Scalp V0 implementado: configuración, manejo de estado, riesgo, ejecución Bybit, persistencia y documentación viva.
- Estrategias probadas y descartadas por profit factor < 1: trend pullback (1m), VWAP reversion (1m/5m), range breakout, volume breakout y Bollinger squeeze breakout.
- Activo principal vigente: **SOLUSDT** (linear perpetual, apalancamiento 3).
- Trabajo permitido en V0: solo correcciones de bugs y mejoras operativas menores; no se añaden estrategias nuevas.

## V1 – Futuro (pendiente de autorización)
- Arrancará cuando el usuario confirme explícitamente: *"Continuamos con V1"*.
- Objetivos iniciales:
  - Portar una estrategia validada en Pine con **PF > 1.3**, **200+ trades cerrados** y **drawdown < 20 %**.
  - Integrar la estrategia en la arquitectura existente (sin romper módulos congelados).
  - Mantener sincronizados logs, estadísticas, Excels y documentación automática.
- Alcance opcional:
  - Ajustar parámetros de riesgo y sesiones para SOLUSDT basados en métricas reales.
  - Preparar la migración a otros símbolos solo después de consolidar solidez en SOLUSDT.
