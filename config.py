import os
from typing import List

from dotenv import load_dotenv

print("Loading environment variables...")
load_dotenv(override=True)
print("Environment variables loaded")


class Config:

    def __init__(self):
        self.CLIENT_ID = os.getenv("FLATTRADE_CLIENT_ID")
        self.CLIENT_SECRET = os.getenv("FLATTRADE_CLIENT_SECRET")
        self.REDIRECT_URI = os.getenv("FLATTRADE_REDIRECT_URI", "https://localhost:8000/callback")
        self.API_KEY = os.getenv("FLATTRADE_API_KEY")
        self.PASSWORD = os.getenv("FLATTRADE_PASSWORD")
        self.PAN = os.getenv("FLATTRADE_PAN")
        self.POSITIONS_URL = os.getenv("FLATTRADE_POSITIONS_URL")
        self.TOKEN_URL = os.getenv("FLATTRADE_TOKEN_URL")
        self.FINAL_TOKEN = os.getenv("FLATTRADE_TOKEN")
        self.WS_TIMEOUT_SECONDS = int(os.getenv("FLATTRADE_WS_TIMEOUT", "60"))  # Default 60 seconds

    def validate(self) -> None:
        required_vars: List[str] = ["CLIENT_ID", "CLIENT_SECRET", "API_KEY", "PASSWORD", "PAN"]
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("All required environment variables are set")
