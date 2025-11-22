from pybit.unified_trading import HTTP
client = HTTP(testnet=True, api_key="x", api_secret="y")
print("attrs:", dir(client))
