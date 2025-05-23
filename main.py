#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Điểm chạy chính của ứng dụng Arbitrage Bot.
"""
import os
import sys
import time
import asyncio
import argparse
import logging
import concurrent.futures
from colorama import Style, Fore, init
from dotenv import load_dotenv

# Khởi tạo colorama
init()

# Import các dịch vụ
from services.exchange_service import ExchangeService
from services.balance_service import BalanceService
from services.order_service import OrderService
from services.notification_service import NotificationService

# Import các bot
from bots.classic_bot import ClassicBot
from bots.delta_neutral_bot import DeltaNeutralBot
from bots.fake_money_bot import FakeMoneyBot

# Import các module tiện ích
from utils.logger import log_info, log_error, log_warning, logger
from utils.helpers import show_time
from configs import PYTHON_COMMAND, ENABLE_TELEGRAM, BOT_MODES


def setup_logging(level=logging.INFO):
    """
    Thiết lập cấu hình logging nâng cao.
    
    Args:
        level: Cấp độ logging (mặc định là INFO)
    """
    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs('logs', exist_ok=True)
    
    # Định dạng thời gian cho tên file log
    log_filename = f"logs/arbitrage_bot_{time.strftime('%Y-%m-%d')}.log"
    
    # Định dạng cho các message log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Cấu hình logging
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )


def display_banner():
    """Hiển thị banner khi khởi động ứng dụng."""
    print("""
                ╔═╗─╔╗────────────────╔═╗─╔╗─────────╔══╗───╔╗
                ║║╚╗║║────────────────║║╚╗║║─────────║╔╗║───║║
                ║╔╗╚╝╠══╦╗╔╦╗─╔╦══╦═╗─║╔╗╚╝╠══╦══╦══╗║╚╝╚╦═╗║╚═╗
                ║║╚╗║║╔╗║║║║║─║║║═╣╔╗╗║║╚╗║║╔╗║╔╗║╔═╝║╔═╗║╔╗╣╔╗║
                ║║─║║║╚╝║╚╝║╚═╝║║═╣║║║║║─║║║╚╝║╚╝║╚═╗║╚═╝║║║║║║║
                ╚╝─╚═╩═╗╠══╩═╗╔╩══╩╝╚╝╚╝─╚═╩═╗╠══╩══╝╚═══╩╝╚╩╝╚╝
                ─────╔═╝║──╔═╝║────────────╔═╝║
                ─────╚══╝──╚══╝────────────╚══╝
    """)
    print(f"\n{Fore.CYAN}AWS Arbitrage Bot{Style.RESET_ALL} - Giao dịch chênh lệch giá crypto tự động")
    print("\nGithub: nguyenngocbinh\nTwitter: @nanabi88\n")


def parse_arguments():
    """
    Phân tích tham số dòng lệnh.
    
    Returns:
        argparse.Namespace: Đối tượng chứa tham số dòng lệnh
    """
    parser = argparse.ArgumentParser(description='Arbitrage Bot - Giao dịch chênh lệch giá crypto')
    
    # Tham số bắt buộc
    parser.add_argument('mode', choices=BOT_MODES, help='Chế độ bot (fake-money, classic, delta-neutral)')
    parser.add_argument('renew_time', type=int, help='Thời gian làm mới (phút)')
    parser.add_argument('usdt_amount', type=float, help='Số lượng USDT để giao dịch')
    
    # Các sàn giao dịch
    parser.add_argument('exchange1', help='Sàn giao dịch 1')
    parser.add_argument('exchange2', help='Sàn giao dịch 2')
    parser.add_argument('exchange3', help='Sàn giao dịch 3')
    
    # Tham số tùy chọn
    parser.add_argument('symbol', nargs='?', help='Cặp giao dịch (nếu bỏ trống sẽ tìm tự động)')
    
    # Thêm các tùy chọn mới
    parser.add_argument('--debug', action='store_true', help='Kích hoạt chế độ debug')
    parser.add_argument('--no-banner', action='store_true', help='Không hiển thị banner')
    parser.add_argument('--dry-run', action='store_true', help='Chạy mà không thực hiện giao dịch thực tế')
    
    return parser.parse_args()


def get_user_input():
    """
    Lấy thông tin từ người dùng qua giao diện dòng lệnh.
    
    Returns:
        dict: Thông tin nhập từ người dùng
    """
    inputs = {}
    
    # Danh sách các thông tin cần nhập
    input_list = [
        "mode (fake-money, classic, delta-neutral)",
        "renew time (in minutes)",
        "balance to use (USDT)",
        "exchange 1",
        "exchange 2",
        "exchange 3",
        "crypto pair (để trống để tìm tự động)"
    ]
    
    print(f"{Fore.YELLOW}Nhập thông tin cấu hình:{Style.RESET_ALL}")
    # Lấy thông tin từ người dùng
    for prompt in input_list:
        user_input = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} >>> ")
        key = prompt.split(" ")[0]
        inputs[key] = user_input
    
    print()  # Dòng trống cho đẹp
    return inputs


async def find_best_symbol(exchange_service, exchanges):
    """
    Tìm cặp giao dịch tốt nhất cho arbitrage.
    
    Args:
        exchange_service (ExchangeService): Dịch vụ sàn giao dịch
        exchanges (list): Danh sách tên các sàn giao dịch
    
    Returns:
        str: Ký hiệu của cặp giao dịch tốt nhất
    """
    log_info("Đang tìm cặp giao dịch tốt nhất... (có thể mất vài phút)")
    
    try:
        # Danh sách các cặp giao dịch phổ biến để kiểm tra
        common_pairs = [
            "BTC/USDT", "ETH/USDT", "XRP/USDT", "LTC/USDT", "ADA/USDT",
            "DOT/USDT", "DOGE/USDT", "SOL/USDT", "AVAX/USDT", "MATIC/USDT"
        ]
        
        # Danh sách để lưu chênh lệch giá của các cặp giao dịch
        pair_spreads = []
        
        # Kiểm tra từng cặp giao dịch
        for pair in common_pairs:
            try:
                # Lấy giá bid và ask trên mỗi sàn
                bid_prices = {}
                ask_prices = {}
                
                # Thu thập giá từ các sàn
                for exchange_id in exchanges:
                    ticker = exchange_service.get_ticker(exchange_id, pair)
                    bid_prices[exchange_id] = ticker['bid']
                    ask_prices[exchange_id] = ticker['ask']
                
                # Tìm giá bán thấp nhất và giá mua cao nhất
                min_ask = min(ask_prices.values())
                max_bid = max(bid_prices.values())
                
                # Tính chênh lệch giá
                spread = (max_bid - min_ask) / min_ask * 100
                
                # Thêm vào danh sách
                pair_spreads.append((pair, spread))
                
                log_info(f"Cặp {pair}: Chênh lệch giá {spread:.4f}%")
                
            except Exception as e:
                log_warning(f"Không thể lấy thông tin cho cặp {pair}: {str(e)}")
        
        # Sắp xếp các cặp theo chênh lệch giá giảm dần
        pair_spreads.sort(key=lambda x: x[1], reverse=True)
        
        if pair_spreads:
            # Lấy cặp có chênh lệch giá cao nhất
            best_pair = pair_spreads[0][0]
            log_info(f"Đã tìm thấy cặp giao dịch tốt nhất: {best_pair} với chênh lệch giá {pair_spreads[0][1]:.4f}%")
            
            # Lưu cặp giao dịch vào tệp
            with open('symbol.txt', 'w') as f:
                f.write(best_pair)
            
            return best_pair
        else:
            # Nếu không tìm thấy cặp nào, sử dụng BTC/USDT làm mặc định
            default_pair = "BTC/USDT"
            log_warning(f"Không tìm thấy cặp giao dịch phù hợp. Sử dụng mặc định: {default_pair}")
            
            with open('symbol.txt', 'w') as f:
                f.write(default_pair)
            
            return default_pair
            
    except Exception as e:
        log_error(f"Lỗi khi tìm cặp giao dịch tốt nhất: {str(e)}")
        
        # Sử dụng cặp mặc định trong trường hợp lỗi
        default_pair = "BTC/USDT"
        log_warning(f"Sử dụng cặp giao dịch mặc định: {default_pair}")
        
        with open('symbol.txt', 'w') as f:
            f.write(default_pair)
        
        return default_pair


async def run_bot(mode, symbol, usdt_amount, renew_time, exchanges, dry_run=False):
    """
    Chạy bot giao dịch với các tham số đã cho.
    
    Args:
        mode (str): Chế độ bot (fake-money, classic, delta-neutral)
        symbol (str): Ký hiệu của cặp giao dịch
        usdt_amount (float): Số lượng USDT để giao dịch
        renew_time (int): Thời gian làm mới (phút)
        exchanges (list): Danh sách tên các sàn giao dịch
        dry_run (bool): Nếu True, bot sẽ không thực hiện giao dịch thực tế
        
    Returns:
        float: Tổng lợi nhuận (phần trăm)
    """
    try:
        # Khởi tạo các dịch vụ
        exchange_service = ExchangeService()
        balance_service = BalanceService(exchange_service)
        order_service = OrderService(exchange_service)
        notification_service = NotificationService(ENABLE_TELEGRAM)
        
        # Log thông tin khởi động
        log_info(f"Khởi động bot với chế độ: {mode}, số tiền: {usdt_amount} USDT, thời gian làm mới: {renew_time} phút")
        if dry_run:
            log_info("Chế độ dry-run được kích hoạt - không thực hiện giao dịch thực tế")
        
        # Khởi tạo balance files
        balance_service.initialize_balance_files(usdt_amount)
        
        # Tìm cặp giao dịch nếu không được chỉ định
        if not symbol:
            symbol = await find_best_symbol(exchange_service, exchanges)
        else:
            log_info(f"Sử dụng cặp giao dịch đã chỉ định: {symbol}")
        
        # Khởi tạo bot dựa trên chế độ
        if mode == "fake-money" or dry_run:
            bot = FakeMoneyBot(exchange_service, balance_service, order_service, notification_service)
            log_info("Sử dụng bot mô phỏng (không thực hiện giao dịch thực tế)")
        elif mode == "classic":
            bot = ClassicBot(exchange_service, balance_service, order_service, notification_service)
            log_info("Sử dụng bot arbitrage cổ điển")
        elif mode == "delta-neutral":
            bot = DeltaNeutralBot(exchange_service, balance_service, order_service, notification_service)
            log_info("Sử dụng bot delta-neutral")
        else:
            log_error(f"Chế độ không hợp lệ: {mode}")
            return 0
        
        # Cấu hình bot
        timeout = renew_time * 60  # Chuyển đổi phút sang giây
        bot.configure(symbol, exchanges, timeout, usdt_amount, symbol)
        
        # Chạy bot
        start_time = time.time()
        profit_pct = await bot.start()
        end_time = time.time()
        
        # Log thông tin kết thúc
        elapsed_time = time.strftime('%H:%M:%S', time.gmtime(end_time - start_time))
        log_info(f"Bot đã kết thúc sau {elapsed_time}. Tổng lợi nhuận: {profit_pct:.4f}%")
        
        return profit_pct
        
    except Exception as e:
        log_error(f"Lỗi khi chạy bot: {str(e)}")
        return 0


async def main():
    """Hàm chính của ứng dụng."""
    try:
        # Thiết lập logging
        setup_logging()
        
        # Nếu có tham số dòng lệnh
        if len(sys.argv) > 1:
            args = parse_arguments()
            
            # Thiết lập cấp độ logging dựa trên tham số --debug
            if args.debug:
                setup_logging(logging.DEBUG)
                log_info("Chế độ debug được kích hoạt")
            
            # Hiển thị banner nếu không có tham số --no-banner
            if not args.no_banner:
                display_banner()
            
            mode = args.mode
            renew_time = args.renew_time
            usdt_amount = args.usdt_amount
            exchanges = [args.exchange1, args.exchange2, args.exchange3]
            symbol = args.symbol
            dry_run = args.dry_run
            
        # Nếu không có tham số dòng lệnh, lấy thông tin từ người dùng
        else:
            # Hiển thị banner
            display_banner()
            
            inputs = get_user_input()
            
            mode = inputs["mode"]
            renew_time = int(inputs["renew"])
            usdt_amount = float(inputs["balance"])
            exchanges = [inputs["exchange"], inputs["exchange"], inputs["exchange"]]
            symbol = inputs["crypto"] if inputs["crypto"] else None
            dry_run = False  # Mặc định không phải dry run khi nhập thủ công
        
        # Kiểm tra chế độ
        if mode not in BOT_MODES:
            log_error(f"Chế độ không hợp lệ: {mode}. Các chế độ hợp lệ: {', '.join(BOT_MODES)}")
            sys.exit(1)
            
        # Chạy bot
        i = 0
        while True:
            # Chạy bot với các tham số đã cho
            profit_pct = await run_bot(mode, symbol, usdt_amount, renew_time, exchanges, dry_run)
            
            # Đọc số dư mới từ tệp
            with open('balance.txt', 'r') as f:
                usdt_amount = float(f.read().strip())
            
            # Tăng số lần chạy
            i += 1
            
            # Nếu là lần chạy đầu tiên mà có lỗi, thoát khỏi vòng lặp
            if i == 1 and profit_pct == 0:
                log_error("Chạy bot lần đầu không thành công. Thoát chương trình.")
                break
            
    except KeyboardInterrupt:
        log_info("Đã nhận tín hiệu ngắt. Thoát chương trình.")
    except Exception as e:
        log_error(f"Lỗi không xác định: {str(e)}")
    finally:
        log_info("Chương trình kết thúc.")


if __name__ == "__main__":
    # Tải biến môi trường
    load_dotenv()
    
    # Cấu hình mã hóa cho đầu vào/đầu ra
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    
    # Chạy hàm main với asyncio
    asyncio.run(main())