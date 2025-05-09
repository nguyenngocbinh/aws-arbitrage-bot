"""
Bot mô phỏng giao dịch với tiền ảo, không thực hiện giao dịch thực tế.
"""
import time
import asyncio
from asyncio import gather
import ccxt.pro

from utils.logger import log_info, log_error, log_warning
from utils.exceptions import ArbitrageError
from utils.helpers import calculate_average
from bots.base_bot import BaseBot
from config import EXCHANGE_FEES


class FakeMoneyBot(BaseBot):
    """
    Bot mô phỏng giao dịch với tiền ảo, không thực hiện giao dịch thực tế.
    """
    
    def __init__(self, exchange_service, balance_service, order_service, notification_service):
        """
        Khởi tạo bot mô phỏng.
        
        Args:
            exchange_service (ExchangeService): Dịch vụ sàn giao dịch
            balance_service (BalanceService): Dịch vụ quản lý số dư
            order_service (OrderService): Dịch vụ quản lý lệnh
            notification_service (NotificationService): Dịch vụ thông báo
        """
        super().__init__(
            exchange_service, 
            balance_service, 
            order_service, 
            notification_service,
            {'fees': EXCHANGE_FEES}
        )
    
    async def start(self):
        """
        Bắt đầu chạy bot mô phỏng.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        try:
            log_info(f"Bắt đầu phiên mô phỏng với tham số: {self.symbol}, {self.exchanges}, {self.howmuchusd} USDT")
            self.start_time = time.time()
            
            # Lấy giá trung bình toàn cầu
            average_price = await self.exchange_service.get_global_average_price(self.exchanges, self.symbol)
            
            # Tính số lượng crypto có thể mua
            total_crypto = (self.howmuchusd / 2) / average_price
            
            # Thông báo về lệnh mô phỏng
            log_info(
                f"Nếu đây là tiền thật, các lệnh sẽ được gửi đến đây để mua "
                f"{round(total_crypto / len(self.exchanges), 3)} {self.symbol.split('/')[0]} ở giá {average_price}."
            )
            
            # Khởi tạo số dư ảo
            self.usd = self.balance_service.initialize_balances(self.exchanges, self.symbol, self.howmuchusd)
            self.crypto = self.balance_service.initialize_crypto_balances(
                self.exchanges, self.symbol, average_price, self.howmuchusd
            )
            
            # Cập nhật số lượng crypto mỗi giao dịch
            self.crypto_per_transaction = total_crypto / len(self.exchanges)
            
            # Bắt đầu vòng lặp theo dõi sách lệnh
            await self._start_orderbook_loop()
            
            # Dừng bot
            return await self.stop()
            
        except Exception as e:
            log_error(f"Lỗi khi chạy bot mô phỏng: {str(e)}")
            return 0
    
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
        try:
            # Tạo đối tượng sàn giao dịch ccxt.pro
            pro_exchange = await self.exchange_service.get_pro_exchange(exchange_id)
            
            # Theo dõi sách lệnh cho đến khi hết thời gian
            while time.time() <= self.timeout:
                try:
                    # Lấy thông tin sách lệnh mới nhất
                    orderbook = await pro_exchange.watch_order_book(self.symbol)
                    
                    # Xử lý dữ liệu sách lệnh
                    await self.process_orderbook(exchange_id, orderbook)
                    
                except Exception as loop_error:
                    log_error(f"Lỗi trong vòng lặp {exchange_id}: {str(loop_error)}")
                    break
            
            # Đóng kết nối với sàn giao dịch
            await pro_exchange.close()
            
        except Exception as e:
            log_error(f"Lỗi khi khởi tạo vòng lặp cho {exchange_id}: {str(e)}")
    
    async def _execute_trade(self, min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd):
        """
        Thực hiện giao dịch mô phỏng (không gửi lệnh thực tế).
        
        Args:
            min_ask_ex (str): Tên sàn có giá mua thấp nhất
            max_bid_ex (str): Tên sàn có giá bán cao nhất
            profit_with_fees_pct (float): Lợi nhuận sau phí tính theo phần trăm
            profit_with_fees_usd (float): Lợi nhuận sau phí tính theo USD
            
        Returns:
            bool: True nếu giao dịch mô phỏng thành công, ngược lại False
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
            
            # Tạo báo cáo giao dịch mô phỏng
            self._display_trade_report(min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd, fee_usd, fee_crypto)
            
            # Trong mô phỏng, không thực sự đặt lệnh, chỉ cập nhật số dư
            
            # Cập nhật giá trước đó
            self.prec_ask_price = self.min_ask_price
            self.prec_bid_price = self.max_bid_price
            
            # Cập nhật số lượng crypto mỗi giao dịch
            self._update_transaction_amount()
            
            return True
            
        except Exception as e:
            log_error(f"Lỗi khi thực hiện giao dịch mô phỏng: {str(e)}")
            return False
    
    async def stop(self):
        """
        Dừng bot mô phỏng.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        # Gọi phương thức dừng của lớp cha
        return await super().stop()