from dotenv import load_dotenv
import os

load_dotenv()  # tự động load từ .env vào os.environ

def get_env_var(key, default=None):
    return os.getenv(key, default)
