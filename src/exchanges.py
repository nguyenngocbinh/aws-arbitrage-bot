import ccxt.async_support as ccxt
import asyncio

async def fetch_price(exchange_name, symbol):
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class()
        ticker = await exchange.fetch_ticker(symbol)
        await exchange.close()

        price = ticker['last']
        return {"exchange": exchange_name, "price": price}
    except Exception as e:
        print(f"⚠️ Lỗi lấy giá từ {exchange_name}: {e}")
        return None

async def fetch_prices(exchanges, symbol):
    tasks = [fetch_price(ex, symbol) for ex in exchanges]
    results = await asyncio.gather(*tasks)
    # Loại bỏ các kết quả None nếu có lỗi
    return [r for r in results if r is not None]
