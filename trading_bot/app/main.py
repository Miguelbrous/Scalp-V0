from __future__ import annotations

import logging

from fastapi import FastAPI

from .api import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Trading Bot API", version="0.1.0")
app.include_router(api_router)
