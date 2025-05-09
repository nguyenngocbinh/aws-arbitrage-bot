"""
Service quản lý tương tác với các sàn giao dịch.
"""
import os
import ccxt
import ccxt.pro
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from utils.logger import log_info, log_error
from utils.exceptions import ExchangeError, InsufficientBalanceError
from utils.helpers import calculate_average

# Tải biến môi trường
load_dotenv()


class ExchangeService:
    """
    Lớp dịch vụ tương tác với các sàn giao dịch cryptocurrency.
    """
    
    def __init__(self):
        """Khởi tạo dịch vụ sàn giao dịch."""
        self.exchanges = {}
        self.exchange_instances = {}
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Khởi tạo đối tượng sàn giao dịch với thông tin xác thực từ biến môi trường."""
        # Khởi tạo Binance
        if os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_SECRET'):
            self.exchanges['binance'] = {
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET')
            }
        
        # Khởi tạo KuCoin
        if os.getenv('KUCOIN_API_KEY') and os.getenv('KUCOIN_SECRET') and os.getenv('KUCOIN_PASSWORD'):
            self.exchanges['kucoin'] = {
                'apiKey': os.getenv('KUCOIN_API_KEY'),
                'secret': os.getenv('KUCOIN_SECRET'),
                'password': os.getenv('KUCOIN_PASSWORD')
            }
            self.exchanges['kucoinfutures'] = {
                'apiKey': os.getenv('KUCOIN_API_KEY'),
                'secret': os.getenv('KUCOIN_SECRET'),
                'password': os.getenv('KUCOIN_PASSWORD')
            }
        
        # Khởi tạo Bybit
        if os.getenv('BYBIT_API_KEY') and os.getenv('BYBIT_SECRET'):
            self.exchanges['bybit'] = {
                'apiKey': os.getenv('BYBIT_API_KEY'),
                'secret': os.getenv('BYBIT_SECRET'),
                'options': {'defaultType': 'spot'}
            }
        
        # Khởi tạo OKX
        if os.getenv('OKX_API_KEY') and os.getenv('OKX_SECRET') and os.getenv('OKX_PASSWORD'):
            self.exchanges['okx'] = {
                'apiKey': os.getenv('OKX_API_KEY'),
                'secret': os.getenv('OKX_SECRET'),
                'password': os.getenv('OKX_PASSWORD')
            }
    
    def get_exchange(self, exchange_id):
        """
        Lấy đối tượng sàn giao dịch theo id.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
        
        Returns:
            object: Đối tượng sàn giao dịch đã được khởi tạo
        
        Raises:
            ExchangeError: Nếu sàn giao dịch không tồn tại hoặc không được hỗ trợ
        """
        if exchange_id not in self.exchange_instances:
            if exchange_id not in self.exchanges:
                raise ExchangeError(exchange_id, "Sàn giao dịch không được hỗ trợ hoặc chưa được cấu hình")
            
            try:
                # Tạo đối tượng sàn giao dịch
                exchange_class = getattr(ccxt, exchange_id)
                self.exchange_instances[exchange_id] = exchange_class(self.exchanges[exchange_id])
                log_info(f"Đã khởi tạo sàn giao dịch {exchange_id}")
            except Exception as e:
                raise ExchangeError(exchange_id, f"Không thể khởi tạo sàn giao dịch: {str(e)}")
        
        return self.exchange_instances[exchange_id]

    async def get_pro_exchange(self, exchange_id):
        """
        Lấy đối tượng sàn giao dịch ccxt.pro theo id.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
        
        Returns:
            object: Đối tượng sàn giao dịch ccxt.pro đã được khởi tạo
        
        Raises:
            ExchangeError: Nếu sàn giao dịch không tồn tại hoặc không được hỗ trợ
        """
        if exchange_id not in self.exchanges:
            raise ExchangeError(exchange_id, "Sàn giao dịch không được hỗ trợ hoặc chưa được cấu hình")
        
        try:
            # Tạo đối tượng sàn giao dịch pro
            exchange_class = getattr(ccxt.pro, exchange_id)
            return exchange_class(self.exchanges[exchange_id])
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể khởi tạo sàn giao dịch pro: {str(e)}")
    
    def get_balance(self, exchange_id, symbol):
        """
        Lấy số dư của một tài sản trên sàn giao dịch.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của tài sản
        
        Returns:
            float: Số dư của tài sản
        
        Raises:
            ExchangeError: Nếu có lỗi khi lấy số dư
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            # Làm sạch symbol nếu nó có dạng BTC/USDT hoặc BTC:USDT
            if symbol.endswith('/USDT'):
                symbol = symbol[:-5]
            elif symbol.endswith(':USDT'):
                symbol = symbol[:-5]
            
            balance = exchange.fetch_balance()
            
            if symbol in balance['free'] and balance['free'][symbol] != 0:
                return balance['free'][symbol]
            return 0
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể lấy số dư của {symbol}: {str(e)}")
    
    def get_ticker(self, exchange_id, symbol):
        """
        Lấy thông tin ticker của một cặp giao dịch.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            dict: Thông tin ticker
        
        Raises:
            ExchangeError: Nếu có lỗi khi lấy ticker
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.fetch_ticker(symbol)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể lấy ticker cho {symbol}: {str(e)}")
    
    def create_limit_buy_order(self, exchange_id, symbol, amount, price):
        """
        Tạo lệnh mua giới hạn.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
            amount (float): Số lượng cần mua
            price (float): Giá mua
        
        Returns:
            dict: Thông tin lệnh đã tạo
        
        Raises:
            ExchangeError: Nếu có lỗi khi tạo lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.create_limit_buy_order(symbol, amount, price)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể tạo lệnh mua giới hạn cho {symbol}: {str(e)}")
    
    def create_limit_sell_order(self, exchange_id, symbol, amount, price):
        """
        Tạo lệnh bán giới hạn.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
            amount (float): Số lượng cần bán
            price (float): Giá bán
        
        Returns:
            dict: Thông tin lệnh đã tạo
        
        Raises:
            ExchangeError: Nếu có lỗi khi tạo lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.create_limit_sell_order(symbol, amount, price)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể tạo lệnh bán giới hạn cho {symbol}: {str(e)}")
    
    def create_market_buy_order(self, exchange_id, symbol, amount):
        """
        Tạo lệnh mua thị trường.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
            amount (float): Số lượng cần mua
        
        Returns:
            dict: Thông tin lệnh đã tạo
        
        Raises:
            ExchangeError: Nếu có lỗi khi tạo lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.create_market_buy_order(symbol, amount)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể tạo lệnh mua thị trường cho {symbol}: {str(e)}")
    
    def create_market_sell_order(self, exchange_id, symbol, amount):
        """
        Tạo lệnh bán thị trường.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
            amount (float): Số lượng cần bán
        
        Returns:
            dict: Thông tin lệnh đã tạo
        
        Raises:
            ExchangeError: Nếu có lỗi khi tạo lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.create_market_sell_order(symbol, amount)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể tạo lệnh bán thị trường cho {symbol}: {str(e)}")
    
    def fetch_open_orders(self, exchange_id, symbol):
        """
        Lấy danh sách lệnh đang mở.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            list: Danh sách các lệnh đang mở
        
        Raises:
            ExchangeError: Nếu có lỗi khi lấy danh sách lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.fetch_open_orders(symbol)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể lấy danh sách lệnh đang mở cho {symbol}: {str(e)}")
    
    def fetch_closed_orders(self, exchange_id, symbol):
        """
        Lấy danh sách lệnh đã đóng.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            list: Danh sách các lệnh đã đóng
        
        Raises:
            ExchangeError: Nếu có lỗi khi lấy danh sách lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.fetch_closed_orders(symbol)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể lấy danh sách lệnh đã đóng cho {symbol}: {str(e)}")
    
    def cancel_order(self, exchange_id, order_id, symbol):
        """
        Hủy một lệnh.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            order_id (str): ID của lệnh cần hủy
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            dict: Thông tin lệnh đã hủy
        
        Raises:
            ExchangeError: Nếu có lỗi khi hủy lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            return exchange.cancel_order(order_id, symbol)
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể hủy lệnh {order_id} cho {symbol}: {str(e)}")
    
    def cancel_all_orders(self, exchange_id, symbol):
        """
        Hủy tất cả các lệnh đang mở.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            dict: Thông tin về việc hủy lệnh
        
        Raises:
            ExchangeError: Nếu có lỗi khi hủy lệnh
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            if exchange.has['cancelAllOrders']:
                return exchange.cancel_all_orders(symbol)
            else:
                # Nếu sàn không hỗ trợ hủy tất cả, hủy từng lệnh một
                orders = self.fetch_open_orders(exchange_id, symbol)
                results = []
                for order in orders:
                    results.append(self.cancel_order(exchange_id, order['id'], symbol))
                return results
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể hủy tất cả lệnh cho {symbol}: {str(e)}")
    
    def get_precision_min(self, exchange_id, symbol):
        """
        Lấy giá trị tối thiểu của giá cho một cặp giao dịch.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            float: Giá trị tối thiểu
        
        Raises:
            ExchangeError: Nếu có lỗi khi lấy giá trị tối thiểu
        """
        exchange = self.get_exchange(exchange_id)
        
        try:
            symbol_info = exchange.load_markets()[symbol]
            return symbol_info['limits']['price']['min']
        except Exception as e:
            # Nếu không lấy được thông tin, trả về giá trị mặc định
            log_error(f"Không thể lấy giá trị tối thiểu cho {symbol} trên {exchange_id}: {str(e)}")
            return 0.001
    
    async def get_global_average_price(self, exchanges, symbol):
        """
        Lấy giá trung bình của một cặp giao dịch trên nhiều sàn.
        
        Args:
            exchanges (list): Danh sách ID của các sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            float: Giá trung bình
            
        Raises:
            ExchangeError: Nếu có lỗi khi lấy giá
        """
        all_tickers = []
        log_info(f"Đang lấy giá trung bình trên toàn cầu cho {symbol}...")
        
        try:
            for exchange_id in exchanges:
                ticker = self.get_ticker(exchange_id, symbol)
                all_tickers.append(ticker['bid'])
                all_tickers.append(ticker['ask'])
            
            average_price = calculate_average(all_tickers)
            log_info(f"Giá trung bình {symbol} trong USDT: {average_price}")
            return average_price
        except Exception as e:
            raise ExchangeError("global", f"Không thể lấy giá trung bình: {str(e)}")
    
    async def watch_order_book(self, exchange_id, symbol):
        """
        Theo dõi sách lệnh của một cặp giao dịch.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
        
        Returns:
            dict: Thông tin sách lệnh
            
        Raises:
            ExchangeError: Nếu có lỗi khi theo dõi sách lệnh
        """
        try:
            pro_exchange = await self.get_pro_exchange(exchange_id)
            orderbook = await pro_exchange.watch_order_book(symbol)
            return orderbook
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể theo dõi sách lệnh cho {symbol}: {str(e)}")
    
    def emergency_convert(self, exchange_id, symbol, keep_percentage=0.01):
        """
        Chuyển đổi khẩn cấp một tài sản sang USDT.
        
        Args:
            exchange_id (str): ID của sàn giao dịch
            symbol (str): Ký hiệu của cặp giao dịch
            keep_percentage (float): Phần trăm tài sản giữ lại (0.01 = 1%)
        
        Returns:
            dict: Thông tin lệnh bán
            
        Raises:
            ExchangeError: Nếu có lỗi khi chuyển đổi
        """
        try:
            # Hủy tất cả các lệnh đang mở
            self.cancel_all_orders(exchange_id, symbol)
            
            # Lấy số dư và tính số lượng cần bán
            balance = self.get_balance(exchange_id, symbol)
            balance_to_sell = balance - (balance * keep_percentage)
            
            # Kiểm tra số dư tối thiểu
            ticker = self.get_ticker(exchange_id, symbol)
            min_amount_in_base = 10 / ticker['last']  # Số lượng tối thiểu tương đương 10 USDT
            
            if balance_to_sell > min_amount_in_base:
                return self.create_market_sell_order(exchange_id, symbol, round(balance_to_sell, 4))
            else:
                log_info(f"Không đủ {symbol.split('/')[0]} trên {exchange_id}.")
                return None
        except Exception as e:
            raise ExchangeError(exchange_id, f"Không thể thực hiện chuyển đổi khẩn cấp cho {symbol}: {str(e)}")