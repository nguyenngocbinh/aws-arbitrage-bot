import asyncio
import logging
from src.exchanges import fetch_prices
from src.notifier import send_telegram_alert
from src.database import log_spread
from configs import EXCHANGES, SPREAD_THRESHOLD, EXCHANGE_FEES
from utils.helpers import now_utc_str, format_usd

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def run_bot(mode="test", balance=1000, exchanges=["binance", "kraken"], symbol="BTC/USDT"):
    """
    Chạy bot arbitrage để kiểm tra chênh lệch giá giữa các sàn
    
    Args:
        mode (str): "live" để gửi cảnh báo thực, "test" chỉ ghi log
        balance (float): Số tiền mô phỏng để tính lợi nhuận
        exchanges (list): Danh sách các sàn giao dịch cần kiểm tra
        symbol (str): Cặp tiền tệ để kiểm tra (ví dụ: "BTC/USDT")
    """
    try:
        # Xác thực định dạng symbol
        if '/' not in symbol:
            logger.error(f"❌ Định dạng symbol không hợp lệ: {symbol}. Định dạng mong đợi: BTC/USDT")
            return
            
        # Step 1: Fetch prices
        prices = await fetch_prices(exchanges, symbol)

        if len(prices) < 2:
            logger.warning("⚠️ Không đủ sàn để so sánh. Cần ít nhất 2 sàn.")
            return

        # Step 2: Find best buy/sell prices
        sorted_prices = sorted(prices, key=lambda x: x['price'])
        best_buy = sorted_prices[0]
        best_sell = sorted_prices[-1]

        buy_price = best_buy['price']
        sell_price = best_sell['price']
        buy_ex = best_buy['exchange']
        sell_ex = best_sell['exchange']

        # Step 3: Tính phí giao dịch
        buy_fee = EXCHANGE_FEES.get(buy_ex, 0)
        sell_fee = EXCHANGE_FEES.get(sell_ex, 0)

        # Giá hiệu dụng sau phí
        effective_buy = buy_price * (1 + buy_fee)
        effective_sell = sell_price * (1 - sell_fee)

        # Spread sau phí
        net_spread = ((effective_sell - effective_buy) / effective_buy) * 100

        # Step 4: Nếu spread vượt ngưỡng, gửi cảnh báo và log
        if net_spread >= SPREAD_THRESHOLD:
            coin_amount = balance / effective_buy
            profit = (effective_sell - effective_buy) * coin_amount

            # Log thông tin về cơ hội arbitrage
            log_spread(
                symbol=symbol,
                ex_buy=buy_ex,
                price_buy=buy_price,
                ex_sell=sell_ex,
                price_sell=sell_price,
                spread=net_spread,
                mode=mode
            )

            # Tạo nội dung thông báo
            message = (
                f"🚨 [ARBITRAGE ALERT] {symbol}\n"
                f"🟢 BUY  from {buy_ex.upper()} @ {format_usd(buy_price)} (+{buy_fee*100:.2f}% fee)\n"
                f"🔴 SELL to   {sell_ex.upper()} @ {format_usd(sell_price)} (-{sell_fee*100:.2f}% fee)\n"
                f"💥 Net Spread (after fees): {net_spread:.2f}%\n"
                f"💰 Simulated Profit on ${balance}: {format_usd(profit)}\n"
                f"📅 {now_utc_str()} | Mode: {mode.upper()}"
            )
            
            # Chỉ gửi cảnh báo nếu là mode live
            if mode.lower() == "live":
                logger.info(f"Đã phát hiện cơ hội arbitrage: {buy_ex} -> {sell_ex}, spread: {net_spread:.2f}%")
                await send_telegram_alert(message)
            else:
                logger.info(f"[TEST MODE] Phát hiện cơ hội arbitrage nhưng không gửi cảnh báo")
                logger.info(f"Nội dung thông báo:\n{message}")

        else:
            logger.debug(f"Spread sau phí {net_spread:.2f}% < threshold {SPREAD_THRESHOLD}%, bỏ qua.")

    except Exception as e:
        logger.error(f"❌ Lỗi trong run_bot: {e}", exc_info=True)
        # Lỗi nghiêm trọng, thông báo rõ ràng
        if mode.lower() == "live":
            error_message = f"⚠️ Bot gặp lỗi: {str(e)}\nThời gian: {now_utc_str()}"
            await send_telegram_alert(error_message)