import argparse
import asyncio
import logging
import signal
import sys
from bots.arbitrage_bot import run_bot
from configs import EXCHANGES
from utils.helpers import now_utc_str
from src.database import init_db

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """ Phân tích tham số dòng lệnh """
    parser = argparse.ArgumentParser(description="Crypto Arbitrage Bot")
    
    # Các tham số bắt buộc
    parser.add_argument('--mode', required=True, choices=['live', 'test'], help="Chế độ chạy: live hoặc test")
    parser.add_argument('--balance', required=True, type=float, help="Số dư tài khoản cho mỗi giao dịch")
    parser.add_argument('--exchanges', required=True, nargs='+', help="Danh sách các sàn giao dịch tham gia")
    
    # Tham số tùy chọn
    parser.add_argument('--symbol', default="BTC/USDT", help="Cặp giao dịch (mặc định là BTC/USDT)")
    parser.add_argument('--interval', default=60, type=int, help="Khoảng thời gian giữa các lần kiểm tra (giây)")

    return parser.parse_args()

def signal_handler(sig, frame):
    """Xử lý khi nhận tín hiệu kết thúc"""
    logger.info("\nĐang dừng bot một cách an toàn...")
    sys.exit(0)

async def main():
    # Đăng ký handler cho tín hiệu SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Khởi tạo cơ sở dữ liệu
    init_db()
    
    # Phân tích tham số
    args = parse_args()
    
    # Kiểm tra xem sàn giao dịch có hợp lệ không
    valid_exchanges = {ex[0] for ex in EXCHANGES}
    invalid_exchanges = set(args.exchanges) - valid_exchanges
    
    if invalid_exchanges:
        logger.error(f"⚠️ Lỗi: Các sàn giao dịch không hợp lệ: {', '.join(invalid_exchanges)}")
        logger.info(f"Các sàn hợp lệ: {', '.join(valid_exchanges)}")
        return
    
    # In thông tin cấu hình bot
    logger.info(f"\n🔧 Cấu hình Crypto Arbitrage Bot")
    logger.info(f"🔧 Chế độ: {args.mode}")
    logger.info(f"💰 Số dư: {args.balance} USD")
    logger.info(f"💹 Các sàn tham gia: {', '.join(args.exchanges)}")
    logger.info(f"🔗 Cặp giao dịch: {args.symbol}")
    logger.info(f"⏱️ Khoảng thời gian kiểm tra: {args.interval} giây")
    logger.info(f"⏰ Thời gian bắt đầu: {now_utc_str()}")
    
    # Chạy bot liên tục với xử lý lỗi
    try:
        run_count = 0
        consecutive_errors = 0
        while True:
            try:
                run_count += 1
                logger.debug(f"Đang chạy kiểm tra lần thứ {run_count}...")
                
                # Chạy bot với tham số từ dòng lệnh
                await run_bot(
                    mode=args.mode,
                    balance=args.balance,
                    exchanges=args.exchanges,
                    symbol=args.symbol
                )
                
                # Đặt lại bộ đếm lỗi khi thành công
                consecutive_errors = 0
                
                # Chờ đến lần kiểm tra tiếp theo
                logger.debug(f"🕒 Đang chờ {args.interval} giây cho lần kiểm tra tiếp theo...")
                await asyncio.sleep(args.interval)
                
            except Exception as e:
                consecutive_errors += 1
                # Tăng thời gian chờ theo cấp số nhân nhưng giới hạn tối đa
                wait_time = min(10 * (2 ** consecutive_errors), 300)  # Giới hạn ở 5 phút
                
                logger.error(f"❌ Lỗi khi chạy bot: {e}", exc_info=True)
                logger.info(f"⏳ Đang chờ {wait_time} giây trước khi thử lại...")
                await asyncio.sleep(wait_time)
    
    except KeyboardInterrupt:
        logger.info("\nBot đã dừng lại do người dùng nhấn Ctrl+C.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nBot đã dừng lại.")