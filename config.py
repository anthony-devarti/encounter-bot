import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DB_PATH = os.environ.get("DB_PATH", "encounters.db")
README_URL = os.environ.get("README_URL", "https://github.com/YOURNAME/encounter-bot/blob/main/README.md")
