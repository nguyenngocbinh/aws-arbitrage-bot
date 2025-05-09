"""
Các hàm tiện ích dùng chung cho toàn bộ ứng dụng.
"""
import time
from colorama import Style


def show_time():
    """Trả về thời gian hiện tại định dạng HH:MM:SS."""
    return time.strftime('%H:%M:%S', time.gmtime(time.time()))


def format_message(message):
    """
    Format thông báo để hiển thị đúng định dạng và
    loại bỏ các ký tự đặc biệt của colorama.
    """
    message = message.replace("[2m", "")
    message = message.replace("[0m", "")
    return message


def format_log_message(message):
    """Format thông báo log với thời gian."""
    return f"{Style.DIM}[{show_time()}]{Style.RESET_ALL} {message}"


def calculate_average(values):
    """Tính giá trị trung bình của một danh sách số."""
    if not values:
        return 0
    return sum(values) / len(values)


def append_to_file(file_path, content, add_newline=True):
    """Thêm nội dung vào cuối tệp tin."""
    try:
        with open(file_path, 'a+') as file:
            file.seek(0)
            data = file.read(100)
            if len(data) > 0 and add_newline:
                file.write('\n')
            file.write(content)
        return True
    except Exception as e:
        print(f"Lỗi khi ghi vào tệp tin {file_path}: {e}")
        return False


def read_file_content(file_path, default=""):
    """Đọc nội dung của tệp tin."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Lỗi khi đọc tệp tin {file_path}: {e}")
        return default


def update_balance_file(file_path, profit_pct, original_balance):
    """Cập nhật tệp tin số dư với lợi nhuận mới."""
    try:
        new_balance = round(original_balance * (1 + (profit_pct / 100)), 3)
        with open(file_path, 'w') as file:
            file.write(str(new_balance))
        return new_balance
    except Exception as e:
        print(f"Lỗi khi cập nhật tệp tin số dư {file_path}: {e}")
        return original_balance


def extract_base_asset(symbol):
    """Trích xuất tên tài sản cơ sở từ một cặp giao dịch."""
    if symbol.endswith('/USDT'):
        return symbol[:-5]  # Loại bỏ '/USDT'
    if symbol.endswith(':USDT'):
        return symbol[:-5]  # Loại bỏ ':USDT'
    return symbol