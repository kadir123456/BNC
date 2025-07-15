import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings

class BinanceClient:
    """
    Binance Futures API ile etkileşim kurmak için yönetici sınıf.
    REST API (emir gönderme, hesap bilgisi) ve WebSocket (veri akışı) için temel oluşturur.
    """
    def __init__(self):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.base_url = settings.BASE_URL
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")

    async def initialize(self):
        """
        Asenkron istemciyi başlatır. Uygulama başlangıcında çağrılmalıdır.
        """
        if self.client is None:
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
            print("Binance AsyncClient başarıyla başlatıldı.")
        return self.client

    async def close(self):
        """
        İstemci bağlantısını kapatır.
        """
        if self.client:
            await self.client.close_connection()
            self.client = None
            print("Binance AsyncClient bağlantısı kapatıldı.")

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        """
        Stratejiyi 'ısındırmak' için geçmiş mum verilerini çeker.
        """
        try:
            print(f"{symbol} için {limit} adet geçmiş mum verisi çekiliyor...")
            klines = await self.client.get_historical_klines(symbol, interval, limit=limit)
            return klines
        except BinanceAPIException as e:
            print(f"Hata: Geçmiş mum verileri çekilemedi: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        """
        Belirtilen sembol için kaldıracı ayarlar.
        """
        try:
            await self.client.change_leverage(symbol=symbol, leverage=leverage)
            print(f"Başarılı: {symbol} kaldıracı {leverage}x olarak ayarlandı.")
            return True
        except BinanceAPIException as e:
            print(f"Hata: Kaldıraç ayarlanamadı: {e}")
            return False

    async def get_market_price(self, symbol: str) -> float | None:
        """
        Belirtilen sembol için anlık piyasa fiyatını alır.
        """
        try:
            ticker = await self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            print(f"Hata: {symbol} fiyatı alınamadı: {e}")
            return None

    async def create_market_order_with_tp_sl(self, symbol: str, side: str, quantity: float, entry_price: float):
        """
        Ana piyasa emrini ve ona bağlı TP/SL emirlerini oluşturur.
        Bu, projenin en kritik fonksiyonlarından biridir.
        """
        try:
            # 1. Ana PİYASA EMRİNİ GÖNDER
            main_order = await self.client.create_order(
                symbol=symbol,
                side=side,
                type=AsyncClient.ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Başarılı: {symbol} {side} {quantity} PİYASA EMRİ oluşturuldu.")

            await asyncio.sleep(0.5) # Emrin dolması için kısa bir bekleme

            # 2. TP ve SL Fiyatlarını Hesapla
            if side == AsyncClient.SIDE_BUY: # LONG pozisyon için
                tp_price = round(entry_price * (1 + settings.TAKE_PROFIT_PERCENT), 2)
                sl_price = round(entry_price * (1 - settings.STOP_LOSS_PERCENT), 2)
            else: # SHORT pozisyon için
                tp_price = round(entry_price * (1 - settings.TAKE_PROFIT_PERCENT), 2)
                sl_price = round(entry_price * (1 + settings.TAKE_PROFIT_PERCENT), 2)
            
            # 3. TAKE PROFIT EMRİNİ GÖNDER
            await self.client.create_order(
                symbol=symbol,
                side=AsyncClient.SIDE_SELL if side == AsyncClient.SIDE_BUY else AsyncClient.SIDE_BUY,
                type=AsyncClient.ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=tp_price,
                closePosition=True # Pozisyonun tamamını kapat
            )
            print(f"Başarılı: {symbol} için TAKE PROFIT emri {tp_price} seviyesine kuruldu.")

            # 4. STOP LOSS EMRİNİ GÖNDER
            await self.client.create_order(
                symbol=symbol,
                side=AsyncClient.SIDE_SELL if side == AsyncClient.SIDE_BUY else AsyncClient.SIDE_BUY,
                type=AsyncClient.ORDER_TYPE_STOP_MARKET,
                stopPrice=sl_price,
                closePosition=True # Pozisyonun tamamını kapat
            )
            print(f"Başarılı: {symbol} için STOP LOSS emri {sl_price} seviyesine kuruldu.")
            
            return main_order

        except BinanceAPIException as e:
            print(f"Hata: Emir oluşturulurken sorun oluştu: {e}")
            # Hata durumunda açılmış olabilecek pozisyonu kapatmayı deneyebiliriz.
            # Bu, daha gelişmiş bir hata yönetimi gerektirir.
            await self.client.cancel_all_open_orders(symbol=symbol)
            print(f"{symbol} için tüm açık emirler iptal edildi.")
            return None


# Global bir istemci nesnesi oluşturalım.
# Bu nesneyi diğer modüllerden import edip kullanacağız.
binance_client = BinanceClient()