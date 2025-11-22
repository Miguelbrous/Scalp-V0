from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import os

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"


def load_env_secret() -> str | None:
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE)
    return os.getenv("WEBHOOK_SECRET")  # type: ignore[name-defined]


def main():
    parser = argparse.ArgumentParser(
        description="Envía un payload de TradingView de ejemplo al webhook local."
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Host base donde corre la API FastAPI (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="Secreto para el webhook. Si no se indica se intenta leer desde .env.",
    )
    parser.add_argument(
        "--strategy",
        default="EMA_SHORT_SOL_1H",
        help="Nombre de la estrategia configurada en core/config.py",
    )
    parser.add_argument(
        "--symbol",
        default="SOLUSDT",
        help="Símbolo a probar (debe existir en la estrategia).",
    )
    parser.add_argument(
        "--side",
        choices=["long", "short"],
        default="short",
        help="Dirección que se simula.",
    )
    parser.add_argument(
        "--action",
        choices=["entry", "exit"],
        default="entry",
        help="Tipo de acción de TradingView.",
    )
    parser.add_argument(
        "--price",
        type=float,
        default=120.0,
        help="Precio que se enviará en la señal.",
    )
    args = parser.parse_args()

    secret = args.secret or load_env_secret()
    if not secret:
        print("No se encontró WEBHOOK_SECRET en .env ni se pasó por argumento.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "secret": secret,
        "symbol": args.symbol,
        "strategy": args.strategy,
        "side": args.side,
        "action": args.action,
        "price": args.price,
        "timestamp": "2025-11-21T12:00:00Z",
    }

    url = f"{args.host.rstrip('/')}/webhook/tradingview"
    print(f"Enviando señal de prueba a {url} ...")
    response = requests.post(url, json=payload, timeout=10)
    print("Status:", response.status_code)
    try:
        print("Respuesta JSON:", response.json())
    except json.JSONDecodeError:
        print("Respuesta texto:", response.text)


if __name__ == "__main__":
    main()
