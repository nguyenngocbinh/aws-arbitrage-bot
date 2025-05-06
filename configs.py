# configs.py

# Ngưỡng chênh lệch giá (%) sau khi tính phí để kích hoạt cảnh báo
SPREAD_THRESHOLD = 1.0  

# Danh sách các sàn giao dịch hỗ trợ
# Mỗi tuple gồm (id_sàn, tên_hiển_thị)
EXCHANGES = [
    ("binance", "Binance"),
    ("kraken", "Kraken"),
    ("coinbase", "Coinbase"),
    # Thêm sàn khác nếu cần
]

# Phí giao dịch của mỗi sàn (tỷ lệ phần trăm)
EXCHANGE_FEES = {
    "binance": 0.001,   # 0.1%
    "kraken": 0.0026,   # 0.26%
    "coinbase": 0.005,  # 0.5%
    # thêm sàn khác nếu cần
}

# Số lần thử lại khi gặp lỗi kết nối
MAX_RETRIES = 3

# Thời gian chờ tối đa cho mỗi request (giây)
REQUEST_TIMEOUT = 10