import sqlite3
from utils.helpers import now_utc_str

DB_PATH = "arbitrage.db"

def init_db():
    """Khởi tạo database và tạo bảng nếu chưa có"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spreads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            exchange_buy TEXT,
            price_buy REAL,
            exchange_sell TEXT,
            price_sell REAL,
            spread REAL,
            mode TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_spread(symbol, ex_buy, price_buy, ex_sell, price_sell, spread, mode):
    """Ghi log chênh lệch giá vào bảng spreads"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO spreads (
            timestamp, symbol, exchange_buy, price_buy, 
            exchange_sell, price_sell, spread, mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_utc_str(),
        symbol,
        ex_buy,
        price_buy,
        ex_sell,
        price_sell,
        spread,
        mode
    ))
    conn.commit()
    conn.close()

def get_recent_logs(limit=10):
    """Truy xuất các bản ghi gần nhất để debug"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM spreads
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
