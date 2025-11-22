# Trading Bot Skeleton

Esqueleto de un bot 100 % automático basado en señales de TradingView, FastAPI y Bybit. Recibe alertas vía webhook, valida la información, dimensiona el riesgo y envía órdenes reales usando únicamente componentes gratuitos.

## Requisitos

- Python 3.10 o superior.
- Dependencias listadas en `requirements.txt`.
- Cuenta de Bybit (demo o real) con claves API habilitadas.
- Estrategia en TradingView capaz de enviar webhooks JSON.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate  # o source .venv/bin/activate en Linux/Mac
pip install -r requirements.txt
```

Renombra `.env.example` a `.env` y rellena las claves:

```
BYBIT_API_KEY=tu_clave
BYBIT_API_SECRET=tu_secreto
BYBIT_BASE_URL=https://api-testnet.bybit.com
WEBHOOK_SECRET=frase_segura_para_tradingview
DEFAULT_RISK_PER_TRADE=0.01
```

## Ejecución

```bash
uvicorn app.main:app --reload --port 8000
# o usa scripts/run_dev.sh en Linux/Mac
```

Endpoints principales:

- `POST /webhook/tradingview`: recibe la alerta JSON de TradingView.
- `GET /health`: confirma que el servicio está vivo.

## Checklist de verificación (sin TradingView)

1. **Crear `.env`:**
   ```bash
   cp .env.example .env
   # edita los valores con tus claves demo
   ```
2. **Instalar dependencias**: `pip install -r requirements.txt`.
3. **Arrancar la API**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. **Comprobar health**: visita `http://localhost:8000/health` y verifica `{"status":"ok",...}`.
5. **Enviar señal de prueba**:
   ```bash
   python scripts/simulate_signal.py --price 130
   ```
   O usa curl/Postman contra `POST /webhook/tradingview`.
6. **Revisar logs**:
   - `logs/signals.csv` debe registrar la señal.
   - `logs/trades.csv` debe registrar la orden (en testnet el fill se simula con los datos del API).

Si algo falla, revisa la consola de FastAPI y confirma que `WEBHOOK_SECRET` y la estrategia existen en `core/config.py`.

## Flujo resumido

1. TradingView envía una alerta como:
   ```json
   {
     "secret": "frase",
     "symbol": "SOLUSDT",
     "strategy": "EMA_SHORT_SOL_1H",
     "side": "short",
     "action": "entry",
     "price": 145.25,
     "timestamp": "2025-11-21T10:30:00Z"
   }
   ```
2. `app/api.py` valida el secreto y crea un `TradingViewPayload`.
3. `strategies/signal_router.py` traduce la señal en un `OrderIntent` usando la configuración declarada en `core/config.py`.
4. `core/risk.py` calcula la cantidad según el % de riesgo configurado y la distancia al SL.
5. `core/exchange.py` envía la orden a Bybit mediante `pybit`.
6. `core/state.py` y `core/journal.py` guardan el estado de posiciones y los registros CSV.

## Estructura

```
trading_bot/
├─ app/                # FastAPI (router y punto de entrada)
├─ core/               # Config, modelos, exchange, riesgo, estado, journaling
├─ strategies/         # Conversión de señales TradingView -> intents
├─ scripts/            # Scripts utilitarios
└─ logs/               # Salida CSV de señales y operaciones
```

## Próximos pasos sugeridos

- Añadir autenticación (API Keys) al endpoint webhook si lo expones públicamente.
- Añadir SQLite para métricas más detalladas.
- Incluir manejo de reconexión en Bybit (WebSocket) para detectar fills en tiempo real.
- Extender `strategies/signal_router.py` con más estrategias o validaciones específicas.
