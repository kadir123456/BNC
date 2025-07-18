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
        self.exchange_info = None
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")

    async def initialize(self):
        if self.client is None:
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
            self.exchange_info = await self.client.get_exchange_info()
            print("Binance AsyncClient başarıyla başlatıldı ve borsa bilgileri çekildi.")
        return self.client

    async def get_symbol_info(self, symbol: str):
        if not self.exchange_info: return None
        for s in self.exchange_info['symbols']:
            if s['symbol'] == symbol: return s
        return None

    async def get_open_positions(self):
        try:
            positions = await self.client.futures_position_information()
            return [p for p in positions if float(p['positionAmt']) != 0]
        except BinanceAPIException as e:
            print(f"Hata: Pozisyon bilgileri alınamadı: {e}")
            return []

    async def create_market_order_with_tp_sl(self, symbol: str, side: str, quantity: float, entry_price: float, price_precision: int):
        def format_price(price): return f"{price:.{price_precision}f}"
        try:
            main_order = await self.client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
            print(f"Başarılı: {symbol} {side} {quantity} PİYASA EMRİ oluşturuldu.")
            await asyncio.sleep(0.5)
            tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT) if side == 'BUY' else entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
            sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT) if side == 'BUY' else entry_price * (1 + settings.TAKE_PROFIT_PERCENT)
            formatted_tp_price, formatted_sl_price = format_price(tp_price), format_price(sl_price)
            await self.client.futures_create_order(symbol=symbol, side='SELL' if side == 'BUY' else 'BUY', type='TAKE_PROFIT_MARKET', stopPrice=formatted_tp_price, closePosition=True)
            print(f"Başarılı: {symbol} için TAKE PROFIT emri {formatted_tp_price} seviyesine kuruldu.")
            await self.client.futures_create_order(symbol=symbol, side='SELL' if side == 'BUY' else 'BUY', type='STOP_MARKET', stopPrice=formatted_sl_price, closePosition=True)
            print(f"Başarılı: {symbol} için STOP LOSS emri {formatted_sl_price} seviyesine kuruldu.")
            return main_order
        except BinanceAPIException as e:
            print(f"Hata: Emir oluşturulurken sorun oluştu: {e}")
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
            print(f"{symbol} için tüm açık emirler iptal edildi."); return None

    async def close_open_position(self, symbol: str):
        """Belirtilen semboldeki açık pozisyonu piyasa emriyle kapatır."""
        try:
            positions = await self.client.futures_position_information(symbol=symbol)
            for position in positions:
                if float(position['positionAmt']) != 0:
                    side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
                    quantity = abs(float(position['positionAmt']))
                    
                    await self.client.futures_cancel_all_open_orders(symbol=symbol)
                    await asyncio.sleep(0.1) # İptal emrinin işlenmesi için kısa bir bekleme
                    
                    response = await self.client.futures_create_order(
                        symbol=symbol, side=side, type='MARKET',
                        quantity=quantity, reduceOnly=True)
                    print(f"--> TRAILING STOP ile POZİSYON KAPATILDI: {response}")
                    return response
            return None
        except BinanceAPIException as e:
            print(f"Hata: Pozisyon kapatılırken sorun oluştu: {e}")
            return None

    async def close(self):
        if self.client: await self.client.close_connection(); self.client = None; print("Binance AsyncClient bağlantısı kapatıldı.")
    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        try:
            print(f"{symbol} için {limit} adet geçmiş mum verisi çekiliyor..."); return await self.client.get_historical_klines(symbol, interval, limit=limit)
        except BinanceAPIException as e: print(f"Hata: Geçmiş mum verileri çekilemedi: {e}"); return []
    async def set_leverage(self, symbol: str, leverage: int):
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=leverage); print(f"Başarılı: {symbol} kaldıracı {leverage}x olarak ayarlandı."); return True
        except BinanceAPIException as e: print(f"Hata: Kaldıraç ayarlanamadı: {e}"); return False
    async def get_market_price(self, symbol: str):
        try:
            ticker = await self.client.futures_symbol_ticker(symbol=symbol); return float(ticker['price'])
        except BinanceAPIException as e: print(f"Hata: {symbol} fiyatı alınamadı: {e}"); return None

binance_client = BinanceClient()
