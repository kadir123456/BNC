import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle (yerel geliştirme için)
load_dotenv()

class Settings:
    # --- Binance API Ayarları ---
    # Render.com'da Environment Variables olarak ayarlanacak
    # Testnet için https://testnet.binancefuture.com/en/futures/api_manage adresinden alınır
    API_KEY: str = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

    # --- Bot Çalışma Modu ---
    # 'TEST' veya 'LIVE' olarak ayarlanabilir.
    # Bu ayar, kullanılacak API URL'lerini belirler.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "TEST")

    # --- API URL'leri ---
    BASE_URL = "https://fapi.binance.com" if ENVIRONMENT == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if ENVIRONMENT == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 20.0
    # TP ve SL yüzdeleri (örneğin giriş fiyatının %0.6'sı)
    # 1 USDT kar hedefi için (20 USDT * 10x = 200 USDT pozisyon) %0.6'lık bir kar ~1.2 USDT eder.
    # Bu değer işlem ücretlerini karşılar ve net 1 USDT bırakır.
    TAKE_PROFIT_PERCENT: float = 0.006  # %0.6
    STOP_LOSS_PERCENT: float = 0.006   # %0.6 (Risk/Kazanç Oranı 1:1)


# Ayarları global olarak kullanılabilir hale getir
settings = Settings()