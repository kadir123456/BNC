import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- Binance API Ayarları ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")

    # --- Bot Çalışma Modu ---
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    
    # --- Güvenlik Ayarları ---
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")

    # --- API URL'leri ---
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 100.0
    TIMEFRAME: str = "5m"
    
    # TP ve SL yüzdeleri
    TAKE_PROFIT_PERCENT: float = 0.003  # %0.3 Kâr Al
    STOP_LOSS_PERCENT: float = 0.003   # %0.3 Zarar Durdur (Risk/Kazanç Oranı 1:1)

settings = Settings()
