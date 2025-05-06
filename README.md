
# Crypto Arbitrage Bot

## 📜 Giới thiệu
Crypto Arbitrage Bot là một bot sử dụng chiến lược arbitrage để phát hiện các cơ hội chênh lệch giá giữa các sàn giao dịch crypto và gửi cảnh báo qua Telegram khi có cơ hội lớn.

## 🔧 Cấu trúc thư mục

```

aws-arbitrage-bot/
│
├── .env                    # Biến môi trường: API keys, chat ID
├── configs.py              # Cấu hình chung: đường dẫn, pairs, sàn
├── main.py                 # Điểm chạy chính (entry point)
│
├── bots/
│   ├── __init__.py         # Để Python coi là module
│   ├── arbitrage\bots.py   # Bot chính: fetch price, detect spread, notify, log
│
├── src/
│   ├── __init__.py         # Để Python coi là module
│   ├── exchanges.py        # Wrapper API ccxt và async price fetch
│   ├── database.py         # Hàm SQLite: init, insert, query
│   ├── notifier.py         # Gửi cảnh báo qua Telegram (hoặc email)
│
├── utils/
│   ├── __init__.py         # Để Python coi là module
│   └── helpers.py          # Hàm phụ trợ: format price, timestamp,...
│
└── requirements.txt        # Danh sách thư viện cần cài

````

## 🚀 Cài đặt

### Bước 1: Clone repository

Clone project về máy:

```bash
git clone https://github.com/nguyenngocbinh/aws-arbitrage-bot.git
cd aws-arbitrage-bot
````

### Bước 2: Cài đặt các thư viện

Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

### Bước 3: Cấu hình

Tạo một file `.env` trong thư mục gốc và thêm các giá trị sau:

```env
BOT_TOKEN=your_bot_token
CHAT_ID=your_chat_id
```

* **`BOT_TOKEN`**: Token của bot Telegram.
* **`CHAT_ID`**: ID chat của bạn hoặc group chat để nhận thông báo.

### Bước 4: Chạy bot

Chạy bot với lệnh sau:

```bash
python main.py --mode live --balance 1000 --exchanges binance kraken --symbol BTC/USDT
```

Hoặc nếu chỉ muốn chạy ở chế độ kiểm tra:

```bash
python main.py --mode test --balance 1000 --exchanges binance kraken
```

## 📈 Tính năng

1. **Phát hiện chênh lệch giá**: Bot sẽ kiểm tra giá của một cặp coin (ví dụ: BTC/USDT) trên nhiều sàn giao dịch và tính toán chênh lệch (spread).
2. **Gửi cảnh báo**: Nếu chênh lệch giá vượt qua ngưỡng được cấu hình, bot sẽ gửi cảnh báo qua Telegram.
3. **Ghi log vào SQLite**: Các cơ hội arbitrage sẽ được lưu vào cơ sở dữ liệu SQLite để truy xuất và phân tích sau này.
4. **Hỗ trợ nhiều sàn**: Dễ dàng cấu hình thêm các sàn giao dịch và cặp giao dịch trong file `configs.py`.

## 🔧 Cấu trúc mã nguồn

### **`bots/arbitrage_bot.py`**:

* Đây là nơi xử lý chính của bot. Nó lấy giá từ các sàn giao dịch, tính toán chênh lệch và gửi cảnh báo.

### **`src/exchanges.py`**:

* Wrapper cho các API của các sàn giao dịch sử dụng thư viện `ccxt`. Bot sử dụng `asyncio` để lấy giá bất đồng bộ từ các sàn.

### **`src/database.py`**:

* Chứa các hàm để kết nối và ghi log vào cơ sở dữ liệu SQLite.

### **`src/notifier.py`**:

* Gửi cảnh báo qua Telegram khi phát hiện cơ hội arbitrage.

### **`utils/helpers.py`**:

* Các hàm phụ trợ như `format_usd` (định dạng tiền tệ) và `now_utc_str` (lấy thời gian UTC hiện tại).

## ⚙️ Cấu hình và mở rộng

* **Thêm sàn giao dịch**: Bạn có thể dễ dàng thêm các sàn giao dịch mới trong file `src/exchanges.py` và cấu hình trong `configs.py`.
* **Thay đổi ngưỡng cảnh báo**: Điều chỉnh ngưỡng chênh lệch giá trong file `.env` (biến `THRESHOLD`).

## 📜 License

Crypto Arbitrage Bot là phần mềm mã nguồn mở, được phát hành dưới giấy phép MIT. Bạn có thể tự do sử dụng và chỉnh sửa mã nguồn.

## 🤝 Liên hệ

Nếu bạn gặp phải bất kỳ vấn đề nào, đừng ngần ngại mở một **issue** hoặc liên hệ qua email: `youremail@example.com`.
