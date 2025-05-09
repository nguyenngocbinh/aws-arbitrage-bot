"""
Bot giao dịch chênh lệch giá cổ điển, mua ở sàn giá thấp và bán ở sàn giá cao.
"""
import time
import asyncio
from asyncio import gather
import ccxt.pro
import traceback

from utils.logger import log_info, log_error, log_warning, log_debug
from utils.exceptions import ArbitrageError, ExchangeError, InsufficientBalanceError, OrderError
from utils.helpers import calculate_average
from bots.base_bot import BaseBot
from config import EXCHANGE_FEES


class ClassicBot(BaseBot):
    """
    Bot giao dịch chênh lệch giá cổ điển, mua ở sàn giá thấp và bán ở sàn giá cao.
    """
    
    def __init__(self, exchange_service, balance_service, order_service, notification_service):
        """
        Khởi tạo bot giao dịch chênh lệch giá cổ điển.
        
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
        
        # Thêm biến theo dõi số lần thử lại và thống kê
        self.retry_count = 0
        self.max_retries = 3
        self.error_counts = {
            'balance': 0,
            'order': 0,
            'network': 0,
            'other': 0
        }
        self.stats = {
            'opportunities_found': 0,
            'trades_executed': 0,
            'failed_trades': 0,
            'total_volume': 0
        }
    
    async def start(self):
        """
        Bắt đầu chạy bot giao dịch.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        try:
            log_info(f"Bắt đầu phiên giao dịch với tham số: {self.symbol}, {self.exchanges}, {self.howmuchusd} USDT")
            self.start_time = time.time()
            
            # Kiểm tra số dư
            try:
                self.balance_service.check_balances(self.exchanges, 'USDT', self.howmuchusd, self.notification_service)
            except InsufficientBalanceError as e:
                log_error(f"Không đủ số dư: {str(e)}")
                self.error_counts['balance'] += 1
                return 0
            
            # Lấy giá trung bình toàn cầu
            try:
                average_price = await self.exchange_service.get_global_average_price(self.exchanges, self.symbol)
                log_info(f"Giá trung bình toàn cầu cho {self.symbol}: {average_price}")
            except Exception as e:
                log_error(f"Không thể lấy giá trung bình toàn cầu: {str(e)}")
                self.error_counts['network'] += 1
                
                # Thử lại với phương pháp dự phòng
                try:
                    log_warning("Đang thử lại với phương pháp lấy giá dự phòng...")
                    prices = []
                    for exchange_id in self.exchanges:
                        try:
                            ticker = self.exchange_service.get_ticker(exchange_id, self.symbol)
                            prices.append((ticker['bid'] + ticker['ask']) / 2)
                        except Exception:
                            continue
                    
                    if prices:
                        average_price = sum(prices) / len(prices)
                        log_info(f"Giá trung bình dự phòng cho {self.symbol}: {average_price}")
                    else:
                        log_error("Không thể lấy giá từ bất kỳ sàn nào")
                        return 0
                except Exception as backup_error:
                    log_error(f"Cả phương pháp dự phòng cũng thất bại: {str(backup_error)}")
                    return 0
            
            # Tính số lượng crypto có thể mua
            total_crypto = (self.howmuchusd / 2) / average_price
            crypto_per_exchange = total_crypto / len(self.exchanges)
            log_info(f"Số lượng {self.symbol.split('/')[0]} có thể mua: {total_crypto}, mỗi sàn: {crypto_per_exchange}")
            
            # Khởi tạo số dư ảo
            self.usd = self.balance_service.initialize_balances(self.exchanges, self.symbol, self.howmuchusd)
            self.crypto = {exchange: 0 for exchange in self.exchanges}  # Khởi tạo số dư crypto bằng 0
            
            # Đặt lệnh mua ban đầu
            success = False
            for attempt in range(self.max_retries):
                try:
                    log_info(f"Lần thử {attempt+1}/{self.max_retries} đặt lệnh mua ban đầu")
                    success = self.order_service.place_initial_orders(
                        self.exchanges, self.symbol, crypto_per_exchange, average_price, self.notification_service
                    )
                    if success:
                        break
                except OrderError as e:
                    log_error(f"Lỗi khi đặt lệnh mua ban đầu (lần thử {attempt+1}): {str(e)}")
                    self.error_counts['order'] += 1
                    await asyncio.sleep(2)  # Đợi một chút trước khi thử lại
            
            if not success:
                log_warning("Không thể đặt lệnh mua ban đầu sau nhiều lần thử. Dừng bot.")
                return 0
                
            # Cập nhật số dư crypto sau khi đặt lệnh mua ban đầu
            self.crypto = self.balance_service.initialize_crypto_balances(
                self.exchanges, self.symbol, average_price, self.howmuchusd
            )
            
            # Cập nhật số lượng crypto mỗi giao dịch
            self.crypto_per_transaction = (total_crypto / len(self.exchanges)) * 0.99  # Giảm 1% để đảm bảo đủ số dư
            
            # Bắt đầu vòng lặp theo dõi sách lệnh
            await self._start_orderbook_loop()
            
            # Hiển thị thống kê trước khi kết thúc
            self._display_stats()
            
            # Dừng bot
            return await self.stop()
            
        except Exception as e:
            log_error(f"Lỗi khi chạy bot: {str(e)}")
            log_debug(f"Chi tiết lỗi: {traceback.format_exc()}")
            
            # Thực hiện bán khẩn cấp nếu có lỗi
            try:
                self.balance_service.emergency_convert_all(self.symbol, self.exchanges)
            except Exception as cleanup_error:
                log_error(f"Lỗi khi bán khẩn cấp: {str(cleanup_error)}")
                
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
            log_debug(f"Chi tiết lỗi: {traceback.format_exc()}")
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
            
            connection_errors = 0
            max_connection_errors = 5
            reconnect_delay = 5  # giây
            
            # Theo dõi sách lệnh cho đến khi hết thời gian
            while time.time() <= self.timeout:
                try:
                    # Lấy thông tin sách lệnh mới nhất
                    orderbook = await pro_exchange.watch_order_book(self.symbol)
                    
                    # Đặt lại bộ đếm lỗi kết nối khi thành công
                    if connection_errors > 0:
                        log_info(f"Kết nối lại thành công với {exchange_id}")
                        connection_errors = 0
                    
                    # Xử lý dữ liệu sách lệnh
                    opportunity_found = await self.process_orderbook(exchange_id, orderbook)
                    
                    if opportunity_found:
                        self.stats['opportunities_found'] += 1
                    
                except ccxt.pro.NetworkError as network_error:
                    connection_errors += 1
                    log_warning(f"Lỗi kết nối với {exchange_id} (lần {connection_errors}/{max_connection_errors}): {str(network_error)}")
                    
                    if connection_errors >= max_connection_errors:
                        log_error(f"Đã vượt quá số lần thử kết nối với {exchange_id}. Đang khởi động lại kết nối...")
                        
                        # Đóng kết nối hiện tại
                        await pro_exchange.close()
                        
                        # Tạo kết nối mới
                        pro_exchange = await self.exchange_service.get_pro_exchange(exchange_id)
                        connection_errors = 0
                        log_info(f"Đã khởi động lại kết nối với {exchange_id}")
                    
                    # Đợi trước khi thử lại
                    await asyncio.sleep(reconnect_delay)
                    
                except Exception as loop_error:
                    log_error(f"Lỗi trong vòng lặp {exchange_id}: {str(loop_error)}")
                    log_debug(f"Chi tiết lỗi: {traceback.format_exc()}")
                    
                    # Đợi một chút trước khi tiếp tục
                    await asyncio.sleep(1)
                    
                    # Không thoát vòng lặp, tiếp tục thử lại
                
                # Đợi một chút để giảm tải cho CPU
                await asyncio.sleep(0.1)
            
            # Đóng kết nối với sàn giao dịch
            log_info(f"Kết thúc theo dõi sách lệnh trên sàn {exchange_id}")
            if pro_exchange:
                await pro_exchange.close()
                
        except Exception as e:
            log_error(f"Lỗi khi khởi tạo vòng lặp cho {exchange_id}: {str(e)}")
            log_debug(f"Chi tiết lỗi: {traceback.format_exc()}")
            
            # Đảm bảo kết nối được đóng đúng cách
            if pro_exchange:
                try:
                    await pro_exchange.close()
                except Exception:
                    pass
    
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
            
            # Ghi log thông tin về cơ hội giao dịch
            log_info(
                f"Cơ hội giao dịch #{self.opportunity_count}: "
                f"Mua trên {min_ask_ex} ở giá {self.min_ask_price}, "
                f"Bán trên {max_bid_ex} ở giá {self.max_bid_price}, "
                f"Lợi nhuận: {profit_with_fees_pct:.4f}% ({profit_with_fees_usd:.4f} USD)"
            )
            
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
            
            # Thực hiện giao dịch thực tế
            trade_success = self.order_service.place_arbitrage_orders(
                min_ask_ex, max_bid_ex, self.symbol,
                self.crypto_per_transaction, self.min_ask_price, self.max_bid_price,
                self.notification_service
            )
            
            # Cập nhật thống kê
            if trade_success:
                self.stats['trades_executed'] += 1
                self.stats['total_volume'] += self.crypto_per_transaction * self.min_ask_price
                
                # Tạo báo cáo giao dịch
                self._display_trade_report(min_ask_ex, max_bid_ex, profit_with_fees_pct, profit_with_fees_usd, fee_usd, fee_crypto)
            else:
                self.stats['failed_trades'] += 1
                log_warning(f"Giao dịch #{self.opportunity_count} thất bại")
            
            # Cập nhật giá trước đó
            self.prec_ask_price = self.min_ask_price
            self.prec_bid_price = self.max_bid_price
            
            # Cập nhật số lượng crypto mỗi giao dịch
            self._update_transaction_amount()
            
            return trade_success
            
        except Exception as e:
            self.stats['failed_trades'] += 1
            log_error(f"Lỗi khi thực hiện giao dịch: {str(e)}")
            log_debug(f"Chi tiết lỗi: {traceback.format_exc()}")
            return False
    
    def _display_stats(self):
        """Hiển thị thống kê về phiên giao dịch."""
        elapsed_time = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
        
        log_info("\n" + "="*50)
        log_info(f"THỐNG KÊ PHIÊN GIAO DỊCH - {self.symbol}")
        log_info("="*50)
        log_info(f"Thời gian chạy: {elapsed_time}")
        log_info(f"Tổng lợi nhuận: {self.total_absolute_profit_pct:.4f}% ({(self.total_absolute_profit_pct/100)*self.howmuchusd:.4f} USDT)")
        log_info(f"Số cơ hội phát hiện: {self.stats['opportunities_found']}")
        log_info(f"Số giao dịch thành công: {self.stats['trades_executed']}")
        log_info(f"Số giao dịch thất bại: {self.stats['failed_trades']}")
        log_info(f"Tổng khối lượng giao dịch: {self.stats['total_volume']:.4f} USDT")
        
        if self.stats['trades_executed'] > 0:
            avg_profit = self.total_absolute_profit_pct / self.stats['trades_executed']
            log_info(f"Lợi nhuận trung bình mỗi giao dịch: {avg_profit:.4f}%")
        
        log_info("THỐNG KÊ LỖI:")
        log_info(f"- Lỗi số dư: {self.error_counts['balance']}")
        log_info(f"- Lỗi đặt lệnh: {self.error_counts['order']}")
        log_info(f"- Lỗi mạng: {self.error_counts['network']}")
        log_info(f"- Lỗi khác: {self.error_counts['other']}")
        log_info("="*50 + "\n")
        
        # Gửi thông báo tổng kết qua Telegram
        if self.notification_service:
            stats_message = (
                f"📊 THỐNG KÊ PHIÊN GIAO DỊCH - {self.symbol}\n\n"
                f"⏱️ Thời gian chạy: {elapsed_time}\n"
                f"💰 Tổng lợi nhuận: {self.total_absolute_profit_pct:.4f}% ({(self.total_absolute_profit_pct/100)*self.howmuchusd:.4f} USDT)\n"
                f"🔍 Số cơ hội phát hiện: {self.stats['opportunities_found']}\n"
                f"✅ Số giao dịch thành công: {self.stats['trades_executed']}\n"
                f"❌ Số giao dịch thất bại: {self.stats['failed_trades']}\n"
                f"📈 Tổng khối lượng: {self.stats['total_volume']:.4f} USDT"
            )
            self.notification_service.send_message(stats_message)
    
    async def stop(self):
        """
        Dừng bot giao dịch và thực hiện các thao tác dọn dẹp.
        
        Returns:
            float: Tổng lợi nhuận (phần trăm)
        """
        # Bán tất cả crypto trên tất cả sàn
        try:
            log_info(f"Bán tất cả {self.symbol} trên {self.exchanges}")
            self.balance_service.emergency_convert_all(self.symbol, self.exchanges)
            log_info("Đã bán tất cả crypto thành công")
        except Exception as e:
            log_error(f"Lỗi khi bán crypto: {str(e)}")
        
        # Gọi phương thức dừng của lớp cha
        return await super().stop()