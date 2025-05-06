from datetime import datetime

def format_usd(amount):
    """ Định dạng số thành USD với dấu phân cách hàng nghìn và ký tự '$' """
    return f"${amount:,.2f}"

def now_utc_str():
    """ Lấy thời gian hiện tại theo định dạng UTC """
    return datetime.utcnow().isoformat()
