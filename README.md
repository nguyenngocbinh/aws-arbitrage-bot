
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
├── requirements.txt        # Danh sách thư viện cần cài
│
├── bots/
│   ├── __init__.py
│   ├── base_bot.py        # Bot base class với các hàm chung
│   ├── classic_bot.py     # Bot giao dịch classic arbitrage
│   ├── delta_neutral_bot.py # Bot giao dịch delta neutral
│   └── fake_money_bot.py  # Bot test với tiền ảo
│
├── services/
│   ├── __init__.py
│   ├── balance_service.py  # Quản lý số dư tài khoản
│   ├── exchange_service.py # Tương tác với sàn giao dịch
│   ├── notification_service.py # Gửi thông báo
│   └── order_service.py    # Quản lý lệnh giao dịch
│
└── utils/
    ├── __init__.py
    ├── env_loader.py      # Load biến môi trường
    ├── exceptions.py      # Custom exceptions
    ├── helpers.py         # Các hàm tiện ích
    └── logger.py          # Logging configuration

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
TELEGRAM_TOKEN =your_bot_token
CHAT_ID=your_chat_id
```

* **`TELEGRAM_TOKEN`**: Token của bot Telegram.
* **`CHAT_ID`**: ID chat của bạn hoặc group chat để nhận thông báo.

### Bước 4: Chạy bot

Chạy bot với lệnh sau:

```bash
python main.py classic 15 1000 binance kucoin okx BTC/USDT
```

Hoặc nếu muốn test với tiền ảo:

```bash
python main.py fake-money 15 1000 binance kucoin okx
```

Các đối số:
1. mode: Chế độ bot (fake-money/classic/delta-neutral)
2. renew_time: Thời gian làm mới (phút)
3. usdt_amount: Số lượng USDT để giao dịch
4. exchange1: Sàn giao dịch thứ nhất
5. exchange2: Sàn giao dịch thứ hai
6. exchange3: Sàn giao dịch thứ ba
7. symbol: (tùy chọn) Cặp tiền giao dịch (VD: BTC/USDT)
```

## 📈 Tính năng

1. **Ba chế độ giao dịch**:
   - **Classic**: Giao dịch arbitrage truyền thống giữa các sàn
   - **Delta Neutral**: Giao dịch với chiến lược cân bằng delta
   - **Fake Money**: Chế độ test với tiền ảo để kiểm thử chiến lược

2. **Quản lý giao dịch thông minh**:
   - Tự động kiểm tra chênh lệch giá giữa các sàn
   - Đặt lệnh với precision phù hợp cho từng sàn
   - Theo dõi trạng thái lệnh và số dư theo thời gian thực

3. **Tính năng an toàn**:
   - Kiểm tra số dư trước khi giao dịch
   - Hủy lệnh tự động nếu không khớp sau thời gian chờ
   - Cơ chế retry cho các API calls thất bại

4. **Thông báo và theo dõi**:
   - Gửi cảnh báo qua Telegram khi có cơ hội giao dịch
   - Log đầy đủ thông tin để debug và phân tích

## 🔧 Cấu trúc mã nguồn

### **`bots/`**:

* `base_bot.py`: Bot base class với các phương thức chung
* `classic_bot.py`: Triển khai bot giao dịch arbitrage truyền thống
* `delta_neutral_bot.py`: Bot giao dịch với chiến lược delta neutral
* `fake_money_bot.py`: Bot test với tiền ảo để kiểm thử chiến lược

### **`services/`**:

* `balance_service.py`: Quản lý số dư tài khoản trên các sàn
* `exchange_service.py`: Tương tác với API của các sàn giao dịch
* `notification_service.py`: Gửi thông báo qua Telegram
* `order_service.py`: Quản lý việc đặt và theo dõi lệnh

### **`utils/`**:

* `env_loader.py`: Load và validate các biến môi trường
* `exceptions.py`: Custom exceptions cho các tình huống lỗi
* `helpers.py`: Các hàm tiện ích dùng chung
* `logger.py`: Cấu hình logging cho toàn bộ ứng dụng

## ⚙️ Cấu hình và mở rộng

* **Thêm sàn giao dịch**: Bạn có thể dễ dàng thêm các sàn giao dịch mới trong file `src/exchanges.py` và cấu hình trong `configs.py`.
* **Thay đổi ngưỡng cảnh báo**: Điều chỉnh ngưỡng chênh lệch giá trong file `.env` (biến `THRESHOLD`).

## 📜 License

Crypto Arbitrage Bot là phần mềm mã nguồn mở, được phát hành dưới giấy phép MIT. Bạn có thể tự do sử dụng và chỉnh sửa mã nguồn.

## 🤝 Liên hệ

Nếu bạn gặp phải bất kỳ vấn đề nào, đừng ngần ngại mở một **issue** hoặc liên hệ qua email: `youremail@example.com`.
