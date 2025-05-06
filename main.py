import argparse
import asyncio
from bots.arbitrage_bot import run_bot
from configs import EXCHANGES
from utils.helpers import now_utc_str

def parse_args():
    """ Phân tích tham số dòng lệnh """
    parser = argparse.ArgumentParser(description="Crypto Arbitrage Bot")
    
    # Các tham số bắt buộc
    parser.add_argument('--mode', required=True, choices=['live', 'test'], help="Chế độ chạy: live hoặc test")
    parser.add_argument('--balance', required=True, type=float, help="Số dư tài khoản cho mỗi giao dịch")
    parser.add_argument('--exchanges', required=True, nargs='+', help="Danh sách các sàn giao dịch tham gia")
    
    # Tham số tùy chọn
    parser.add_argument('--symbol', default="BTC/USDT", help="Cặp giao dịch (mặc định là BTC/USDT)")

    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Kiểm tra xem sàn giao dịch có hợp lệ không
    valid_exchanges = {ex[0] for ex in EXCHANGES}
    invalid_exchanges = set(args.exchanges) - valid_exchanges
    if invalid_exchanges:
        print(f"⚠️ Lỗi: Các sàn giao dịch không hợp lệ: {', '.join(invalid_exchanges)}")
        return
    
    # In thông tin cấu hình bot
    print(f"\n🔧 Chế độ: {args.mode}")
    print(f"💰 Số dư: {args.balance} USD")
    print(f"💹 Các sàn tham gia: {', '.join(args.exchanges)}")
    print(f"🔗 Cặp giao dịch: {args.symbol}")
    print(f"⏰ Thời gian bắt đầu: {now_utc_str()}")
    
    # Chạy bot liên tục mà không có thời gian làm mới
    while True:
        await run_bot()
        print("🕒 Đang chờ kiểm tra lại các sàn và giao dịch...")
        await asyncio.sleep(1)  # Chạy liên tục, có thể thay đổi thời gian chờ tại đây

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot đã dừng lại.")
