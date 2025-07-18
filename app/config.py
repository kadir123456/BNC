import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ... (Diğer ayarlarınız aynı kalacak) ...

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 100.0
    TIMEFRAME: str = "5m"
    
    # --- Kâr/Zarar Ayarları ---
    TAKE_PROFIT_PERCENT: float = 0.003  # %0.3 Nihai Kâr Al Hedefi
    STOP_LOSS_PERCENT: float = 0.003   # %0.3 Başlangıç Zarar Durdur
    
    # --- YENİ: Kâr Koruma Ayarları (Trailing Stop) ---
    TRAILING_ACTIVATION_PERCENT: float = 0.0015 # Kâr %0.15'e ulaştığında iz süren stop devreye girer
    TRAILING_DISTANCE_PERCENT: float = 0.001    # Fiyat zirveden %0.1 geri çekilirse pozisyonu kârla kapat

settings = Settings()
