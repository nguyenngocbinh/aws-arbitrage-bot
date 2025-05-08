import ccxt.async_support as ccxt
import asyncio
import logging

logger = logging.getLogger(__name__)

def is_exchange_supported(exchange_name):
    """Kiểm tra xem sàn giao dịch có được CCXT hỗ trợ không"""
    return exchange_name in ccxt.exchanges

async def fetch_price(exchange_name, symbol, max_retries=3, timeout=10):
    retries = 0
    exchange = None
    
    while retries < max_retries:
        try:
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({'timeout': timeout * 1000})  # timeout tính bằng ms
            ticker = await exchange.fetch_ticker(symbol)
            price = ticker['last']
            return {"exchange": exchange_name, "price": price}
        except Exception as e:
            retries += 1
            logger.warning(f"⚠️ Lỗi lấy giá từ {exchange_name} (lần {retries}/{max_retries}): {e}")
            if retries < max_retries:
                await asyncio.sleep(1)  # Chờ 1 giây trước khi thử lại
            else:
                return None
        finally:
            # Đảm bảo sàn giao dịch luôn được đóng
            if exchange:
                try:
                    await exchange.close()
                except Exception as e:
                    logger.error(f"Lỗi khi đóng kết nối sàn giao dịch: {e}")
