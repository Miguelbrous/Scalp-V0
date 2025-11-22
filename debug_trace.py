import asyncio
from core.models import TradingViewPayload
from app.api import tradingview_webhook

payload = TradingViewPayload(
    secret="frase_super_secreta",
    symbol="SOLUSDT",
    strategy="EMA_SHORT_SOL_1H",
    side="short",
    action="entry",
    price=130.0,
    timestamp="2025-11-21T12:00:00Z",
)

async def main():
    try:
        result = await tradingview_webhook(payload)
        print("Resultado:", result)
    except Exception as exc:
        import traceback
        traceback.print_exc()

asyncio.run(main())
