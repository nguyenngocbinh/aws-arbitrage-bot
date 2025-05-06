import ccxt.async_support as ccxt
import asyncio

async def fetch_price(exchange_name, symbol, max_retries=3, timeout=10):
    retries = 0
    while retries < max_retries:
        try:
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({'timeout': timeout * 1000})  # timeout in ms
            ticker = await exchange.fetch_ticker(symbol)
            await exchange.close()
            
            price = ticker['last']
            return {"exchange": exchange_name, "price": price}
        except Exception as e:
            retries += 1
            print(f"⚠️ Lỗi lấy giá từ {exchange_name} (lần {retries}/{max_retries}): {e}")
            if retries < max_retries:
                await asyncio.sleep(1)  # Chờ 1 giây trước khi thử lại
            else:
                return None

async def fetch_prices(exchanges, symbol):
    tasks = [fetch_price(ex, symbol) for ex in exchanges]
    results = await asyncio.gather(*tasks)
    # Loại bỏ các kết quả None nếu có lỗi
    return [r for r in results if r is not None]
