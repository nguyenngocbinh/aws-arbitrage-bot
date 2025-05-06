# src/notifier.py
from utils.env_loader import get_env_var
import aiohttp

TELEGRAM_TOKEN = get_env_var("TELEGRAM_API_TOKEN")
CHAT_ID = get_env_var("TELEGRAM_CHAT_ID")

async def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram token/chat_id chưa cấu hình")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                print(f"❌ Gửi Telegram thất bại: {await resp.text()}")
