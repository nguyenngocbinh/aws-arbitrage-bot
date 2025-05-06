import asyncio
from src.exchanges import fetch_prices
from src.notifier import send_telegram_alert
from src.database import log_spread
from configs import EXCHANGES, SPREAD_THRESHOLD, EXCHANGE_FEES
from utils.helpers import now_utc_str, format_usd


async def run_bot(mode="test", balance=1000, exchanges=["binance", "kraken"], symbol="BTC/USDT"):
    try:
        # Step 1: Fetch prices
        prices = await fetch_prices(exchanges, symbol)

        if len(prices) < 2:
            print("⚠️ Không đủ sàn để so sánh.")
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

            # Log
            log_spread(
                symbol=symbol,
                ex_buy=buy_ex,
                price_buy=buy_price,
                ex_sell=sell_ex,
                price_sell=sell_price,
                spread=net_spread,
                mode=mode
            )

            # Gửi Telegram
            message = (
                f"🚨 [ARBITRAGE ALERT] {symbol}\n"
                f"🟢 BUY  from {buy_ex.upper()} @ {format_usd(buy_price)} (+{buy_fee*100:.2f}% fee)\n"
                f"🔴 SELL to   {sell_ex.upper()} @ {format_usd(sell_price)} (-{sell_fee*100:.2f}% fee)\n"
                f"💥 Net Spread (after fees): {net_spread:.2f}%\n"
                f"💰 Simulated Profit on ${balance}: {format_usd(profit)}\n"
                f"📅 {now_utc_str()} | Mode: {mode.upper()}"
            )
            await send_telegram_alert(message)

        else:
            print(f"Spread sau phí {net_spread:.2f}% < threshold {SPREAD_THRESHOLD}%, bỏ qua.")

    except Exception as e:
        print(f"❌ Lỗi trong run_bot: {e}")
