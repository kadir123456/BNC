import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle (yerel geliştirme için)
load_dotenv()

class Settings:
    # --- Binance API Ayarları ---
    # Render.com'da Environment Variables olarak ayarlanacak
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")

    # --- Bot Çalışma Modu ---
    # 'TEST' veya 'LIVE' olarak ayarlanabilir.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    
    # --- Güvenlik Ayarları ---
    # Arayüzü korumak için kullanıcı adı ve şifre
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")

    # --- API URL'leri ---
    # ENVIRONMENT değişkenine göre doğru URL'leri seçer
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 50.0
    TIMEFRAME: str = "15m" # <-- EKLENEN YENİ SATIR
    # TP ve SL yüzdeleri (örneğin giriş fiyatının %0.6'sı)
    TAKE_PROFIT_PERCENT: float = 0.006  # %0.6
    STOP_LOSS_PERCENT: float = 0.006   # %0.6 (Risk/Kazanç Oranı 1:1)


# Ayarları global olarak kullanılabilir hale getir
settings = Settings()
