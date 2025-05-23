"""
Bot giao dịch cơ sở với các chức năng chung.
"""
import time
import asyncio
import signal
import sys
from asyncio import gather
import ccxt.pro
from colorama import Fore, Style

from utils.logger import log_info, log_error, log_warning, log_profit, log_opportunity
from utils.exceptions import ArbitrageError, ExchangeError, InsufficientBalanceError, OrderError
from utils.helpers import show_time, extract_base_asset
from configs import PROFIT_CRITERIA_PCT, PROFIT_CRITERIA_USD, ENABLE_CTRL_C_HANDLING


class BaseBot:
    """
    Lớp bot giao dịch cơ sở với các chức năng chung.
    """
    
    def __init__(self, exchange_service, balance_service, order_service, notification_service, config=None):
        """
        Khởi tạo bot giao dịch.
        
        Args:
            exchange_service (ExchangeService): Dịch vụ sàn giao dịch
            balance_service (BalanceService): Dịch vụ quản lý số dư
            order_service (OrderService): Dịch vụ quản lý lệnh
            notification_service (NotificationService): Dịch vụ thông báo
            config (dict, optional): Cấu hình cho bot
        """
        self.exchange_service = exchange_service
        self.balance_service = balance_service
        self.order_service = order_service
        self.notification_service = notification_service
        self.config = config or {}
        
        # Các biến chung
        self.symbol = None
        self.exchanges = []
        self.timeout = 0
        self.howmuchusd = 0
        self.total_absolute_profit_pct = 0
        self.opportunity_count = 0
        self.start_time = 0
        
        # Khởi tạo các biến theo dõi giá
        self.bid_prices = {}  # Giá mua tốt nhất trên mỗi sàn (người khác mua)
        self.ask_prices = {}  # Giá bán tốt nhất trên mỗi sàn (người khác bán)
        self.min_ask_price = 0
        self.max_bid_price = 0
        self.prec_ask_price = 0
        self.prec_bid_price = 0
        
        # Số dư
        self.usd = {}  # Số dư USDT trên mỗi sàn
        self.crypto = {}  # Số dư crypto trên mỗi sàn
        self.crypto_per_transaction = 0  # Số lượng crypto mỗi giao dịch
        
        # Khởi tạo bắt CTRL+C
        if ENABLE_CTRL_C_HANDLING:
            signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def configure(self, symbol, exchanges, timeout, amount_usd, indicatif=None):
        """
        Cấu hình bot giao dịch.
        
        Args:
            symbol (str): Ký hiệu của cặp giao dịch
            exchanges (list): Danh sách tên các sàn giao dịch
            timeout (int): Thời gian chạy tối đa (giây)
            amount_usd (float): Số lượng USDT để giao dịch
            indicatif (str, optional): Tiêu đề cho thông báo
        """
        self.symbol = symbol
        self.exchanges = exchanges
        self.timeout = time.time() + timeout
        self.howmuchusd = float(amount_usd)
        self.indicatif = indicatif or symbol
        
        log_info(f"Cấu hình bot với: {symbol}, {exchanges}, {timeout}s, {amount_usd} USDT")
    
    async def start(self):
        """
        Bắt đầu chạy bot giao dịch.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
            
        Raises:
            NotImplementedError: Phương thức này cần được triển khai ở lớp con
        """
        raise NotImplementedError("Phương thức này cần được triển khai ở lớp con")
    
    async def stop(self):
        """
        Dừng bot giao dịch và thực hiện các thao tác dọn dẹp.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        # Cập nhật số dư với lợi nhuận
        final_balance = self.balance_service.update_balance_with_profit(self.total_absolute_profit_pct)
        
        # Gửi thông báo kết thúc phiên
        message = (
            f"Phiên giao dịch với {self.symbol} đã kết thúc.\n"
            f"Tổng lợi nhuận: {round(self.total_absolute_profit_pct, 4)}% "
            f"({round((self.total_absolute_profit_pct / 100) * self.howmuchusd, 4)} USDT)\n\n"
            f"Tổng số dư hiện tại: {final_balance} USDT"
        )
        log_info(message)
        
        if self.notification_service:
            self.notification_service.send_message(message)
        
        return self.total_absolute_profit_pct
    
    def _handle_interrupt(self, sig, frame):
        """
        Xử lý khi người dùng nhấn Ctrl+C.
        
        Args:
            sig: Tín hiệu nhận được
            frame: Frame hiện tại
        """
        print("\n\n\n")
        
        answered = False
        while not answered:
            try:
                user_input = input(
                    f"{Style.DIM}[{show_time()}]{Style.RESET_ALL} CTRL+C đã được nhấn. "
                    f"Bạn có muốn bán tất cả crypto về USDT không? (y)es / (n)o\n\ninput: "
                )
                
                if user_input.lower() in ["y", "yes"]:
                    answered = True
                    self.balance_service.emergency_convert_all(self.symbol, self.exchanges)
                    sys.exit(1)
                    
                elif user_input.lower() in ["n", "no"]:
                    answered = True
                    sys.exit(1)
                    
            except KeyboardInterrupt:
                # Nếu người dùng nhấn Ctrl+C một lần nữa, thoát ngay lập tức
                sys.exit(1)
    
    async def _start_orderbook_loop(self):
        """
        Bắt đầu vòng lặp theo dõi sách lệnh trên tất cả các sàn.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        try:
            # Tạo các vòng lặp cho từng sàn giao dịch
            exchange_loops = []
            
            for exchange_id in self.exchanges:
                exchange_loops.append(self._exchange_loop(exchange_id))
                
            # Chạy tất cả các vòng lặp
            await gather(*exchange_loops)
            
            return self.total_absolute_profit_pct
            
        except Exception as e:
            log_error(f"Lỗi trong vòng lặp theo dõi sách lệnh: {str(e)}")
            raise
    
    async def _exchange_loop(self, exchange_id):
        """
        Vòng lặp theo dõi sách lệnh cho một sàn giao dịch cụ thể.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            
        Returns:
            None
        """
        pro_exchange = None
        try:
            # Tạo đối tượng sàn giao dịch ccxt.pro
            log_info(f"Bắt đầu theo dõi sách lệnh trên sàn {exchange_id}")
            pro_exchange = await self.exchange_service.get_pro_exchange(exchange_id)
            
            # Theo dõi sách lệnh cho đến khi hết thời gian
            while time.time() <= self.timeout:
                try:
                    # Lấy thông tin sách lệnh mới nhất
                    orderbook = await pro_exchange.watch_order_book(self.symbol)
                    
                    # Xử lý dữ liệu sách lệnh
                    await self.process_orderbook(exchange_id, orderbook)
                    
                except ccxt.pro.NetworkError as network_error:
                    log_warning(f"Lỗi kết nối với {exchange_id}: {str(network_error)}")
                    await asyncio.sleep(1)  # Đợi một chút trước khi thử lại
                    
                except Exception as loop_error:
                    log_error(f"Lỗi trong vòng lặp {exchange_id}: {str(loop_error)}")
                    await asyncio.sleep(1)  # Đợi một chút trước khi thử lại
                
                # Đợi một chút để giảm tải cho CPU
                await asyncio.sleep(0.1)
            
            # Đóng kết nối với sàn giao dịch
            log_info(f"Kết thúc theo dõi sách lệnh trên sàn {exchange_id}")
            if pro_exchange:
                await pro_exchange.close()
                
        except Exception as e:
            log_error(f"Lỗi khi khởi tạo vòng lặp cho {exchange_id}: {str(e)}")
            
            # Đảm bảo kết nối được đóng đúng cách
            if pro_exchange:
                try:
                    await pro_exchange.close()
                except Exception:
                    pass
    
    async def process_orderbook(self, exchange_id, orderbook):
        """
        Xử lý dữ liệu sách lệnh nhận được từ sàn giao dịch.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            orderbook (dict): Dữ liệu sách lệnh
            
        Returns:
            bool: True nếu phát hiện cơ hội giao dịch, ngược lại False
        """
        # Cập nhật giá mua và bán tốt nhất
        self.bid_prices[exchange_id] = orderbook["bids"][0][0]  # Giá mua cao nhất
        self.ask_prices[exchange_id] = orderbook["asks"][0][0]  # Giá bán thấp nhất
        
        # Tìm sàn có giá bán thấp nhất và sàn có giá mua cao nhất
        min_ask_ex = min(self.ask_prices, key=self.ask_prices.get)
        max_bid_ex = max(self.bid_prices, key=self.bid_prices.get)
        
        # Điều chỉnh lựa chọn sàn dựa trên số dư
        for exchange in self.exchanges:
            # Nếu không đủ crypto, chọn sàn này để mua
            if exchange in self.crypto and self.crypto[exchange] < self.crypto_per_transaction:
                min_ask_ex = exchange
                
            # Nếu không đủ USDT (không nên xảy ra), chọn sàn này để bán
            if exchange in self.usd and self.usd[exchange] <= 0:
                max_bid_ex = exchange
        
        # Lấy giá mua và bán tốt nhất đã điều chỉnh
        self.min_ask_price = self.ask_prices[min_ask_ex]
        self.max_bid_price = self.bid_prices[max_bid_ex]
        
        # Tính toán lợi nhuận tiềm năng
        total_usd_amount = sum(self.usd.values())
        
        # Tính lợi nhuận trước phí
        crypto_amount = self.crypto_per_transaction
        profit_usd = crypto_amount * (self.max_bid_price - self.min_ask_price)
        profit_pct = (profit_usd / total_usd_amount) * 100
        
        # Tính phí giao dịch
        fees = self.config.get('fees', {})
        fee_rate_buy = fees.get(min_ask_ex, {}).get('give', 0.001)
        fee_rate_sell = fees.get(max_bid_ex, {}).get('receive', 0.001)
        
        fee_buy = crypto_amount * self.min_ask_price * fee_rate_buy
        fee_sell = crypto_amount * self.max_bid_price * fee_rate_sell
        total_fees = fee_buy + fee_sell
        
        # Tính lợi nhuận sau phí
        profit_with_fees_usd = profit_usd - total_fees
        profit_with_fees_pct = (profit_with_fees_usd / total_usd_amount) * 100
        
        # Hiển thị thông tin về cơ hội tốt nhất
        self._display_best_opportunity(min_ask_ex, max_bid_ex, profit_with_fees_usd)
        
        # Kiểm tra điều kiện để thực hiện giao dịch
        if self._should_execute_trade(min_ask_ex, max_bid_ex, profit_with_fees_usd, profit_with_fees_pct):
            # Thực hiện giao dịch
            await self._execute_trade(min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd)
            return True
            
        return False
    
    def _display_best_opportunity(self, min_ask_ex, max_bid_ex, profit_with_fees_usd):
        """
        Hiển thị thông tin về cơ hội giao dịch tốt nhất hiện tại.
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
            profit_with_fees_usd (float): Lợi nhuận sau phí tính theo USD
        """
        # Xác định màu hiển thị dựa trên lợi nhuận
        if profit_with_fees_usd < 0:
            color = Fore.RED
        elif profit_with_fees_usd > 0:
            color = Fore.GREEN
        else:
            color = Fore.WHITE
        
        # Hiển thị thông tin
        for count in range(0, 1):
            sys.stdout.write("\033[F")
            sys.stdout.write("\033[K")
            
        print(
            f"{Style.DIM}[{show_time()}]{Style.RESET_ALL} "
            f"Cơ hội tốt nhất: {color}{round(profit_with_fees_usd, 4)} USD {Style.RESET_ALL}(sau phí)       "
            f"mua: {min_ask_ex} ở {self.min_ask_price}     bán: {max_bid_ex} ở {self.max_bid_price}"
        )
    
    def _should_execute_trade(self, min_ask_ex, max_bid_ex, profit_with_fees_usd, profit_with_fees_pct):
        """
        Kiểm tra xem có nên thực hiện giao dịch hay không.
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
            profit_with_fees_usd (float): Lợi nhuận sau phí tính theo USD
            profit_with_fees_pct (float): Lợi nhuận sau phí tính theo phần trăm
            
        Returns:
            bool: True nếu nên thực hiện giao dịch, ngược lại False
        """
        # Điều kiện cơ bản: sàn mua và bán phải khác nhau
        if min_ask_ex == max_bid_ex:
            return False
        
        # Kiểm tra điều kiện lợi nhuận
        if profit_with_fees_usd <= float(PROFIT_CRITERIA_USD):
            return False
            
        if profit_with_fees_pct <= float(PROFIT_CRITERIA_PCT):
            return False
        
        # Kiểm tra xem giá có thay đổi so với giao dịch trước đó không
        if self.prec_ask_price == self.min_ask_price and self.prec_bid_price == self.max_bid_price:
            return False
        
        # Kiểm tra đủ số dư để thực hiện giao dịch
        if self.usd[min_ask_ex] < self.crypto_per_transaction * self.min_ask_price * 1.001:
            return False
            
        if self.crypto[max_bid_ex] < self.crypto_per_transaction * 1.001:
            return False
        
        # Nếu qua tất cả các điều kiện, có thể thực hiện giao dịch
        return True
    
    async def _execute_trade(self, min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd):
        """
        Thực hiện giao dịch chênh lệch giá.
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
            profit_with_fees_pct (float): Lợi nhuận sau phí tính theo phần trăm
            profit_with_fees_usd (float): Lợi nhuận sau phí tính theo USD
            
        Returns:
            bool: True nếu giao dịch thành công, ngược lại False
        """
        try:
            # Tăng số lượng cơ hội đã phát hiện
            self.opportunity_count += 1
            
            # Cập nhật số dư trên các sàn
            self._update_balances_after_trade(min_ask_ex, max_bid_ex)
            
            # Tính toán phí giao dịch
            fees = self.config.get('fees', {})
            fee_rate_buy = fees.get(min_ask_ex, {}).get('give', 0.001)
            fee_rate_sell = fees.get(max_bid_ex, {}).get('receive', 0.001)
            
            fee_crypto = self.crypto_per_transaction * (fee_rate_buy + fee_rate_sell)
            fee_usd = (self.crypto_per_transaction * self.max_bid_price * fee_rate_sell) + (self.crypto_per_transaction * self.min_ask_price * fee_rate_buy)
            
            # Cập nhật tổng lợi nhuận
            self.total_absolute_profit_pct += profit_with_fees_pct
            
            # Tạo báo cáo giao dịch
            self._display_trade_report(min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd, fee_usd, fee_crypto)
            
            # Đặt lệnh giao dịch
            self.order_service.place_arbitrage_orders(
                min_ask_ex, max_bid_ex, self.symbol,
                self.crypto_per_transaction, self.min_ask_price, self.max_bid_price,
                self.notification_service
            )
            
            # Cập nhật giá trước đó
            self.prec_ask_price = self.min_ask_price
            self.prec_bid_price = self.max_bid_price
            
            # Cập nhật số lượng crypto mỗi giao dịch
            self._update_transaction_amount()
            
            return True
            
        except Exception as e:
            log_error(f"Lỗi khi thực hiện giao dịch: {str(e)}")
            return False
    
    def _update_balances_after_trade(self, min_ask_ex, max_bid_ex):
        """
        Cập nhật số dư sau khi thực hiện giao dịch.
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
        """
        # Cập nhật số dư trên sàn mua
        fees = self.config.get('fees', {})
        buy_fee_rate = fees.get(min_ask_ex, {}).get('give', 0.001)
        sell_fee_rate = fees.get(max_bid_ex, {}).get('receive', 0.001)
        
        # Tăng số dư crypto trên sàn mua
        self.crypto[min_ask_ex] += self.crypto_per_transaction * (1 - buy_fee_rate)
        
        # Giảm số dư USDT trên sàn mua
        self.usd[min_ask_ex] -= self.crypto_per_transaction * self.min_ask_price * (1 + buy_fee_rate)
        
        # Giảm số dư crypto trên sàn bán
        self.crypto[max_bid_ex] -= self.crypto_per_transaction * (1 + sell_fee_rate)
        
        # Tăng số dư USDT trên sàn bán
        self.usd[max_bid_ex] += self.crypto_per_transaction * self.max_bid_price * (1 - sell_fee_rate)
    
    def _update_transaction_amount(self):
        """
        Cập nhật số lượng crypto mỗi giao dịch.
        """
        # Tính tổng số lượng crypto trên tất cả các sàn
        total_crypto = sum(self.crypto.values())
        
        # Cập nhật số lượng crypto mỗi giao dịch (lấy trung bình)
        self.crypto_per_transaction = total_crypto / len(self.exchanges) * 0.99  # Giảm 1% để đảm bảo đủ số dư
    
    def _display_trade_report(self, min_ask_ex, max_bid_ex, profit_pct, profit_usd, fee_usd, fee_crypto):
        """
        Hiển thị báo cáo về giao dịch đã thực hiện.
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
            profit_pct (float): Lợi nhuận tính theo phần trăm
            profit_usd (float): Lợi nhuận tính theo USD
            fee_usd (float): Phí tính theo USD
            fee_crypto (float): Phí tính theo crypto
        """
        # Xóa dòng hiện tại
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K")
        
        # In đường phân cách
        print("-----------------------------------------------------\n")
        
        # Tạo chuỗi thông tin số dư
        ex_balances = ""
        for exchange in self.exchanges:
            ex_balances += f"\n➝ {exchange}: {round(self.crypto[exchange], 3)} {extract_base_asset(self.symbol)} / {round(self.usd[exchange], 2)} USDT"
        
        # In thông tin giao dịch
        elapsed_time = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
        current_worth = round((self.howmuchusd * (1 + (self.total_absolute_profit_pct / 100))), 3)
        
        print(
            f"{Style.RESET_ALL}Cơ hội #{self.opportunity_count} phát hiện! "
            f"({min_ask_ex} {self.min_ask_price} -> {self.max_bid_price} {max_bid_ex})\n"
            f"\nLợi nhuận: {Fore.GREEN}+{round(profit_pct, 4)}% (+{round(profit_usd, 4)} USD){Style.RESET_ALL}\n"
            f"\nTổng lợi nhuận phiên: {Fore.GREEN}+{round(self.total_absolute_profit_pct, 4)}% "
            f"(+{round((self.total_absolute_profit_pct / 100) * self.howmuchusd, 4)} USD){Style.RESET_ALL}\n"
            f"\nPhí: {Fore.RED}-{round(fee_usd, 4)} USD      -{round(fee_crypto, 4)} {extract_base_asset(self.symbol)}\n"
            f"\n{Style.RESET_ALL}Giá trị hiện tại: {current_worth} USD{Style.RESET_ALL}{Style.DIM}"
            f"{ex_balances}\n"
            f"\nThời gian đã trôi qua: {elapsed_time}\n"
            f"\n{Style.RESET_ALL}-----------------------------------------------------\n"
        )
        
        # Gửi thông báo qua Telegram nếu được kích hoạt
        if self.notification_service:
            self.notification_service.send_opportunity(
                self.opportunity_count, min_ask_ex, self.min_ask_price, max_bid_ex, self.max_bid_price,
                profit_pct, profit_usd, self.total_absolute_profit_pct, 
                (self.total_absolute_profit_pct / 100) * self.howmuchusd,
                fee_usd, fee_crypto, self.symbol, elapsed_time, 
                {ex: {'crypto': self.crypto[ex], 'usd': self.usd[ex]} for ex in self.exchanges},
                current_worth
            )