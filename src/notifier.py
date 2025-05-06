import aiohttp
from configs import TELEGRAM

async def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM['TOKEN']}/sendMessage"
    payload = {
        "chat_id": TELEGRAM["CHAT_ID"],
        "text": message
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, data=payload)
