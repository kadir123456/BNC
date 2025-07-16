import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings

class BinanceClient:
    def __init__(self):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")

    async def initialize(self):
        if self.client is None:
            # Kütüphanenin en doğru şekilde çalışması için testnet ayarını burada yapıyoruz.
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
            print("Binance AsyncClient başarıyla başlatıldı.")
        return self.client

    async def close(self):
        if self.client:
            await self.client.close_connection()
            self.client = None
            print("Binance AsyncClient bağlantısı kapatıldı.")

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        try:
            print(f"{symbol} için {limit} adet geçmiş mum verisi çekiliyor...")
            # Bu fonksiyon hem spot hem futures için ortaktır
            klines = await self.client.get_historical_klines(symbol, interval, limit=limit)
            return klines
        except BinanceAPIException as e:
            print(f"Hata: Geçmiş mum verileri çekilemedi: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        try:
            # Futures'a özel fonksiyon
            await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            print(f"Başarılı: {symbol} kaldıracı {leverage}x olarak ayarlandı.")
            return True
        except BinanceAPIException as e:
            print(f"Hata: Kaldıraç ayarlanamadı: {e}")
            return False

    async def get_market_price(self, symbol: str) -> float | None:
        try:
            # Futures'a özel fonksiyon
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            print(f"Hata: {symbol} fiyatı alınamadı: {e}")
            return None

    async def create_market_order_with_tp_sl(self, symbol: str, side: str, quantity: float, entry_price: float):
        try:
            # DÜZELTME: Emirleri 'futures_create_order' ile gönderiyoruz
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            print(f"Başarılı: {symbol} {side} {quantity} PİYASA EMRİ oluşturuldu.")

            await asyncio.sleep(0.5)

            if side == 'BUY':
                tp_price = round(entry_price * (1 + settings.TAKE_PROFIT_PERCENT), 2)
                sl_price = round(entry_price * (1 - settings.STOP_LOSS_PERCENT), 2)
            else:
                tp_price = round(entry_price * (1 - settings.TAKE_PROFIT_PERCENT), 2)
                sl_price = round(entry_price * (1 + settings.TAKE_PROFIT_PERCENT), 2)

            await self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                closePosition=True
            )
            print(f"Başarılı: {symbol} için TAKE PROFIT emri {tp_price} seviyesine kuruldu.")

            await self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type='STOP_MARKET',
                stopPrice=sl_price,
                closePosition=True
            )
            print(f"Başarılı: {symbol} için STOP LOSS emri {sl_price} seviyesine kuruldu.")
            
            return main_order

        except BinanceAPIException as e:
            print(f"Hata: Emir oluşturulurken sorun oluştu: {e}")
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
            print(f"{symbol} için tüm açık emirler iptal edildi.")
            return None

binance_client = BinanceClient()
