# Comandos del proyecto

Este directorio recopila los comandos clave que se usan en el flujo de trabajo del bot. Cada uno incluye la ruta desde la que debe ejecutarse y lo que hace dentro del proyecto.

## 1. Preparación del entorno

1. `cd trading_bot`
   - **Dónde**: raíz del repositorio (`C:\Users\migue\Desktop\Scalp 0V`).
   - **Función**: entrar en la carpeta principal del bot antes de ejecutar cualquier orden.

2. `py -3.11 -m venv .venv`
   - **Dónde**: dentro de `trading_bot`.
   - **Función**: crea un entorno virtual usando Python 3.11 para aislar dependencias.

3. `.\.venv\Scripts\activate`
   - **Dónde**: `trading_bot`.
   - **Función**: activa el entorno virtual para que todos los comandos posteriores usen esa instalación de Python.

4. `pip install -r requirements.txt`
   - **Dónde**: `trading_bot` con la venv activada.
   - **Función**: instala FastAPI, Uvicorn, pybit y demás librerías necesarias.

## 2. Ejecución del bot

5. `python -m uvicorn app.main:app --reload --port 8000`
   - **Dónde**: `trading_bot` con la venv activa.
   - **Función**: inicia la API FastAPI del bot en `http://localhost:8000`. La opción `--reload` reinicia el servidor cuando cambian los archivos.

6. `python scripts/simulate_signal.py --price 130`
   - **Dónde**: `trading_bot` con la venv activa.
   - **Función**: envía una señal de prueba al endpoint `/webhook/tradingview` usando el `WEBHOOK_SECRET` de `.env`. Permite verificar el flujo sin TradingView real.

## 3. Comprobaciones rápidas

7. `curl http://localhost:8000/health`
   - **Dónde**: cualquier terminal mientras el servidor está activo.
   - **Función**: comprueba que la API responde `{"status":"ok"}` y que no hay errores.

8. `dir logs` (o abrir `logs/signals.csv` y `logs/trades.csv`)
   - **Dónde**: `trading_bot`.
   - **Función**: revisar que las señales y operaciones se están registrando correctamente tras cada prueba.

> Mantén este archivo actualizado si se añaden nuevos comandos importantes al flujo de trabajo.
