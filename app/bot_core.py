import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
import math

class BotCore:
    """
    Botun ana mantığını yöneten sınıf. WebSocket bağlantısını kurar,
    veri akışını işler ve al-sat kararlarını uygular.
    """
    def __init__(self):
        self.status = {
            "is_running": False,
            "symbol": None,
            "in_position": False,
            "status_message": "Bot başlatılmadı.",
            "last_signal": "N/A"
        }
        self.klines = []
        self._stop_requested = False
        self.quantity_precision = 0 # Miktar hassasiyetini saklamak için yeni değişken

    async def start(self, symbol: str):
        """
        Botun ana çalışma döngüsünü başlatır.
        """
        if self.status["is_running"]:
            print("Bot zaten çalışıyor.")
            return

        self._stop_requested = False
        self.status["is_running"] = True
        self.status["symbol"] = symbol
        self.status["in_position"] = False
        self.status["status_message"] = f"{symbol} için başlatılıyor..."
        print(self.status["status_message"])

        await binance_client.initialize()
        
        # YENİ: Sembol bilgilerini ve hassasiyeti al
        symbol_info = await binance_client.get_symbol_info(symbol)
        if not symbol_info:
            self.status["status_message"] = f"{symbol} için borsa bilgileri alınamadı."
            await self.stop() # Hata durumunda botu durdur
            return
        self.quantity_precision = symbol_info['quantityPrecision']
        print(f"{symbol} için miktar hassasiyeti ayarlandı: {self.quantity_precision} ondalık basamak")
        
        leverage_set = await binance_client.set_leverage(symbol, settings.LEVERAGE)
        if not leverage_set:
            self.status["status_message"] = "Kaldıraç ayarlanamadı. Bot durduruluyor."
            await self.stop()
            return

        # İsteğiniz üzerine limiti 50'ye düşürüyoruz
        self.klines = await binance_client.get_historical_klines(symbol, "5m", limit=50)
        if not self.klines:
            self.status["status_message"] = "Geçmiş veri alınamadı. Bot durduruluyor."
            await self.stop()
            return
        
        self.status["status_message"] = f"{symbol} için sinyal bekleniyor..."
        
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_5m"
        try:
            # ping_interval ekleyerek bağlantıyı canlı tutuyoruz.
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                print(f"WebSocket bağlantısı kuruldu: {ws_url} (Ping devrede)")
                while not self._stop_requested:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                        await self._handle_websocket_message(message)
                    except asyncio.TimeoutError:
                        print("WebSocket mesajı zaman aşımına uğradı. Bağlantı kontrol ediliyor...")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket bağlantısı kapandı. Döngü sonlandırılıyor.")
                        break
        except Exception as e:
            print(f"WebSocket bağlantı hatası: {e}")

        await self.stop()

    async def stop(self):
        """
        Botun çalışma döngüsünü güvenli bir şekilde durdurur.
        """
        self._stop_requested = True
        # Zaten çalışan bir stop varsa tekrar çağırmayı önle
        if self.status["is_running"]:
            self.status["is_running"] = False
            self.status["status_message"] = "Bot durduruldu."
            print(self.status["status_message"])
            await binance_client.close()

    async def _handle_websocket_message(self, message: str):
        """
        Gelen WebSocket mesajlarını işler.
        """
        data = json.loads(message)
        
        if data.get('k', {}).get('x', False):
            kline_data = data['k']
            print(f"Yeni mum kapandı: {self.status['symbol']} - Kapanış Fiyatı: {kline_data['c']}")
            
            self.klines.pop(0)
            self.klines.append([
                kline_data['t'], kline_data['o'], kline_data['h'], kline_data['l'], kline_data['c'], kline_data['v'],
                kline_data['T'], kline_data['q'], kline_data['n'], kline_data['V'], kline_data['Q'], '0'
            ])

            if not self.status["in_position"]:
                signal = trading_strategy.analyze_klines(self.klines)
                self.status["last_signal"] = signal
                print(f"Strateji analizi sonucu: {signal}")

                if signal in ["LONG", "SHORT"]:
                    await self._execute_trade(signal)
            else:
                print("Zaten bir pozisyon açık, yeni sinyal işlenmiyor.")

    def _format_quantity(self, quantity: float) -> float:
        """Miktarı, sembolün gerektirdiği doğru ondalık hassasiyetine göre formatlar."""
        if self.quantity_precision == 0:
            return math.floor(quantity)
        
        factor = 10 ** self.quantity_precision
        return math.floor(quantity * factor) / factor

    async def _execute_trade(self, signal: str):
        """
        Belirlenen sinyale göre alım/satım işlemi gerçekleştirir.
        """
        symbol = self.status["symbol"]
        side = "BUY" if signal == "LONG" else "SELL"
        
        self.status["status_message"] = f"{signal} sinyali alındı. İşlem hazırlanıyor..."
        print(self.status["status_message"])

        price = await binance_client.get_market_price(symbol)
        if not price:
            self.status["status_message"] = "İşlem için fiyat alınamadı."
            print(self.status["status_message"])
            return

        position_size = settings.ORDER_SIZE_USDT * settings.LEVERAGE
        unformatted_quantity = position_size / price
        
        # YENİ: Miktarı doğru hassasiyete göre formatla
        quantity = self._format_quantity(unformatted_quantity)
        
        print(f"Hesaplanan Miktar: {unformatted_quantity:.4f} -> Formatlanan Miktar: {quantity} {symbol.replace('USDT','')}")

        if quantity <= 0:
            print("Hesaplanan miktar çok düşük, emir gönderilemiyor.")
            return
        
        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, price)

        if order:
            self.status["in_position"] = True
            self.status["status_message"] = f"{signal} pozisyonu {price} fiyattan açıldı. TP/SL kuruldu."
            print(self.status["status_message"])
        else:
            self.status["status_message"] = "Emir gönderilemedi. Lütfen logları kontrol edin."
            print(self.status["status_message"])

bot_core = BotCore()
