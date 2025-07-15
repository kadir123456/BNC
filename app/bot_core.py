import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy

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
        self.status["in_position"] = False # Her başlangıçta pozisyonda olmadığını varsay
        self.status["status_message"] = f"{symbol} için başlatılıyor..."
        print(self.status["status_message"])

        # 1. Binance istemcisini başlat
        await binance_client.initialize()

        # 2. Kaldıracı ayarla
        leverage_set = await binance_client.set_leverage(symbol, settings.LEVERAGE)
        if not leverage_set:
            self.status["status_message"] = "Kaldıraç ayarlanamadı. Bot durduruluyor."
            self.status["is_running"] = False
            return

        # 3. Stratejiyi 'ısındırmak' için geçmiş verileri çek
        self.klines = await binance_client.get_historical_klines(symbol, "5m", limit=100)
        if not self.klines:
            self.status["status_message"] = "Geçmiş veri alınamadı. Bot durduruluyor."
            self.status["is_running"] = False
            return
        
        self.status["status_message"] = f"{symbol} için sinyal bekleniyor..."
        
        # 4. WebSocket bağlantısını başlat
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_5m"
        async with websockets.connect(ws_url) as ws:
            print(f"WebSocket bağlantısı kuruldu: {ws_url}")
            while not self._stop_requested:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=60.0) # 60sn'de bir mesaj gelmezse hata ver
                    await self._handle_websocket_message(message)
                except asyncio.TimeoutError:
                    print("WebSocket bağlantısı zaman aşımına uğradı. Yeniden bağlanmaya çalışılıyor...")
                    # Yeniden bağlanma mekanizması eklenebilir
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket bağlantısı kapandı. Yeniden bağlanmaya çalışılıyor...")
                    break
        
        # Döngü bittiğinde botu durdur
        await self.stop()


    async def stop(self):
        """
        Botun çalışma döngüsünü güvenli bir şekilde durdurur.
        """
        self._stop_requested = True
        self.status["is_running"] = False
        self.status["status_message"] = f"Bot durduruldu."
        print(self.status["status_message"])
        await binance_client.close()


    async def _handle_websocket_message(self, message: str):
        """
        Gelen WebSocket mesajlarını işler.
        """
        data = json.loads(message)
        
        # Sadece kapanan mumlarla ilgileniyoruz
        if data.get('k', {}).get('x', False):
            kline_data = data['k']
            print(f"Yeni mum kapandı: {self.status['symbol']} - Kapanış Fiyatı: {kline_data['c']}")
            
            # Geçmiş veri listemizi güncelle
            self.klines.pop(0) # En eski mumu sil
            self.klines.append([ # Yeni mumu ekle (formatı get_historical_klines ile uyumlu hale getir)
                kline_data['t'], kline_data['o'], kline_data['h'], kline_data['l'], kline_data['c'], kline_data['v'],
                kline_data['T'], kline_data['q'], kline_data['n'], kline_data['V'], kline_data['Q'], '0'
            ])

            # Pozisyonda değilsek yeni sinyal ara
            if not self.status["in_position"]:
                signal = trading_strategy.analyze_klines(self.klines)
                self.status["last_signal"] = signal
                print(f"Strateji analizi sonucu: {signal}")

                if signal in ["LONG", "SHORT"]:
                    await self._execute_trade(signal)
            else:
                # ÖNEMLİ: TP/SL dolduğunda pozisyon durumunu sıfırlama mekanizması burada olmalı.
                # Şimdilik, botun yeni bir pozisyon açmasını engelliyoruz.
                # Gelişmiş versiyonda, kullanıcının pozisyonlarını dinleyen bir stream açılabilir.
                print("Zaten bir pozisyon açık, yeni sinyal işlenmiyor.")


    async def _execute_trade(self, signal: str):
        """
        Belirlenen sinyale göre alım/satım işlemi gerçekleştirir.
        """
        symbol = self.status["symbol"]
        side = "BUY" if signal == "LONG" else "SELL"
        
        self.status["status_message"] = f"{signal} sinyali alındı. İşlem hazırlanıyor..."
        print(self.status["status_message"])

        # İşlem miktarını hesapla
        price = await binance_client.get_market_price(symbol)
        if not price:
            self.status["status_message"] = "İşlem için fiyat alınamadı."
            print(self.status["status_message"])
            return

        # Miktar = (Pozisyon Büyüklüğü USDT * Kaldıraç) / Fiyat
        # Binance'in istediği hassasiyete yuvarlamak önemlidir. Şimdilik temel hesaplama.
        position_size = settings.ORDER_SIZE_USDT * settings.LEVERAGE
        quantity = round(position_size / price, 3) # BTC/USDT için 3 ondalık hassasiyet genelde yeterli
        
        print(f"Hesaplanan Miktar: {quantity} {symbol.replace('USDT','')}")

        # Emir gönder
        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, price)

        if order:
            self.status["in_position"] = True
            self.status["status_message"] = f"{signal} pozisyonu {price} fiyattan açıldı. TP/SL kuruldu."
            print(self.status["status_message"])
        else:
            self.status["status_message"] = "Emir gönderilemedi. Lütfen logları kontrol edin."
            print(self.status["status_message"])

# Botun ana nesnesini global olarak oluşturalım
bot_core = BotCore()