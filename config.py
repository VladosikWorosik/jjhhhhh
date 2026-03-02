import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8739949603:AAFum6Tg6BRixvbj3qrg3cgbxxONR7jYn5o")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@RyzeKazino")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "7927868527").split(",")]

SPIN_COOLDOWN = 15 * 60  # 15 минут
WIN_AMOUNT = 15          # Звёзды за победу
DATA_DIR = "data"
USERS_FILE = "data/users.json"

WITHDRAWALS_FILE = "data/withdrawals.json"
