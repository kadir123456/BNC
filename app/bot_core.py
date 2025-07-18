import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
import math

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False, "symbol": None, "in_position": False,
            "status_message": "Bot başlatılmadı.", "last_signal": "N/A",
            "entry_price": 0.0, "highest_price": 0.0, "position_side": None # Yeni durum değişkenleri
        }
        self.klines, self._stop_requested, self.quantity_precision, self.price_precision = [], False, 0, 0
    
    # ... (_get_precision_from_filter ve start/stop fonksiyonları aynı kalacak) ...
    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str: return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0
    async def start(self, symbol: str):
        if self.status["is_running"]: print("Bot zaten çalışıyor."); return
        self._stop_requested = False
        self.status.update({"is_running": True, "symbol": symbol, "in_position": False, "status_message": f"{symbol} için başlatılıyor..."})
        print(self.status["status_message"])
        await binance_client.initialize()
        symbol_info = await binance_client.get_symbol_info(symbol)
        if not symbol_info: self.status["status_message"] = f"{symbol} için borsa bilgileri alınamadı."; await self.stop(); return
        self.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
        self.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
        print(f"{symbol} için Miktar Hassasiyeti: {self.quantity_precision}, Fiyat Hassasiyeti: {self.price_precision}")
        if not await binance_client.set_leverage(symbol, settings.LEVERAGE): self.status["status_message"] = "Kaldıraç ayarlanamadı."; await self.stop(); return
        self.klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=50)
        if not self.klines: self.status["status_message"] = "Geçmiş veri alınamadı."; await self.stop(); return
        self.status["status_message"] = f"{symbol} ({settings.TIMEFRAME}) için sinyal bekleniyor..."
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        try:
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                print(f"WebSocket bağlantısı kuruldu: {ws_url} (Ping devrede)")
                while not self._stop_requested:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                        await self._handle_websocket_message(message)
                    except asyncio.TimeoutError: print("WebSocket mesajı zaman aşımına uğradı."); continue
                    except websockets.exceptions.ConnectionClosed: print("WebSocket bağlantısı kapandı."); break
        except Exception as e: print(f"WebSocket bağlantı hatası: {e}")
        await self.stop()
    async def stop(self):
        self._stop_requested = True
        if self.status["is_running"]:
            self.status.update({"is_running": False, "status_message": "Bot durduruldu."})
            print(self.status["status_message"]); await binance_client.close()

    async def _handle_websocket_message(self, message: str):
        data = json.loads(message)
        if data.get('k', {}).get('x', False):
            kline_data = data['k']
            current_price = float(kline_data['c'])
            print(f"Yeni mum kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) - Kapanış Fiyatı: {current_price}")
            
            self.klines.pop(0); self.klines.append([kline_data[key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
            
            if self.status["in_position"]:
                # --- YENİ: TRAILING STOP (İZ SÜREN STOP) MANTIĞI ---
                is_long = self.status["position_side"] == "LONG"
                highest_price = self.status.get("highest_price", self.status["entry_price"])
                lowest_price = self.status.get("lowest_price", self.status["entry_price"])

                # Kâr koruma mekanizmasının devreye girip girmediğini kontrol et
                activation_price_long = self.status["entry_price"] * (1 + settings.TRAILING_ACTIVATION_PERCENT)
                activation_price_short = self.status["entry_price"] * (1 - settings.TRAILING_ACTIVATION_PERCENT)
                
                trailing_active = (is_long and current_price > activation_price_long) or \
                                  (not is_long and current_price < activation_price_short)

                if trailing_active:
                    if is_long:
                        # Zirve fiyatı güncelle
                        if current_price > highest_price:
                            self.status["highest_price"] = current_price
                            print(f"--> YENİ ZİRVE: {current_price:.4f}. İz süren stop ayarlanıyor.")
                        # Zirveden geri çekilmeyi kontrol et
                        trailing_stop_price = self.status["highest_price"] * (1 - settings.TRAILING_DISTANCE_PERCENT)
                        if current_price < trailing_stop_price:
                            print(f"--> KÂR KORUMA (TRAILING STOP) TETİKLENDİ! Fiyat {self.status['highest_price']:.4f} zirvesinden {trailing_stop_price:.4f} altına düştü. Pozisyon kapatılıyor.")
                            await binance_client.close_open_position(self.status["symbol"])
                            self.status["in_position"] = False
                            return # Mum analizini bitir
                    else: # SHORT pozisyon için
                        # Dip fiyatı güncelle
                        if current_price < lowest_price:
                            self.status["lowest_price"] = current_price
                            print(f"--> YENİ DİP: {current_price:.4f}. İz süren stop ayarlanıyor.")
                        # Dipten geri yükselişi kontrol et
                        trailing_stop_price = self.status["lowest_price"] * (1 + settings.TRAILING_DISTANCE_PERCENT)
                        if current_price > trailing_stop_price:
                            print(f"--> KÂR KORUMA (TRAILING STOP) TETİKLENDİ! Fiyat {self.status['lowest_price']:.4f} dibinden {trailing_stop_price:.4f} üstüne çıktı. Pozisyon kapatılıyor.")
                            await binance_client.close_open_position(self.status["symbol"])
                            self.status["in_position"] = False
                            return # Mum analizini bitir

                # --- TRAILING STOP MANTIĞI SONU ---

                # Pozisyonun TP/SL ile kapanıp kapanmadığını kontrol et
                open_positions = await binance_client.get_open_positions()
                if not any(p['symbol'] == self.status['symbol'] for p in open_positions):
                    print(f"--> Pozisyon (TP/SL) kapandı. Yeni sinyaller dinleniyor.")
                    self.status.update({"in_position": False, "status_message": f"{self.status['symbol']} için sinyal bekleniyor..."})
            
            if not self.status["in_position"]:
                signal = trading_strategy.analyze_klines(self.klines)
                self.status["last_signal"] = signal; print(f"Strateji analizi sonucu: {signal}")
                if signal in ["LONG", "SHORT"]: await self._execute_trade(signal)

    # _format_quantity fonksiyonu aynı kalacak
    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0: return math.floor(quantity)
        factor = 10 ** self.quantity_precision; return math.floor(quantity * factor) / factor

    async def _execute_trade(self, signal: str):
        # ... (başlangıç kısmı aynı) ...
        symbol = self.status["symbol"]; side = "BUY" if signal == "LONG" else "SELL"
        self.status["status_message"] = f"{signal} sinyali alındı..."; print(self.status["status_message"])
        price = await binance_client.get_market_price(symbol)
        if not price: self.status["status_message"] = "İşlem için fiyat alınamadı."; return
        quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / price)
        print(f"Hesaplanan Miktar: {quantity} {symbol.replace('USDT','')}")
        if quantity <= 0: print("Hesaplanan miktar çok düşük, emir gönderilemiyor."); return
        
        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, price, self.price_precision)
        
        if order:
            # YENİ: Pozisyon bilgilerini kaydet
            self.status.update({
                "in_position": True, 
                "status_message": f"{signal} pozisyonu {price} fiyattan açıldı.",
                "entry_price": price,
                "position_side": signal,
                "highest_price": price, # Long için zirve takibi
                "lowest_price": price   # Short için dip takibi
            })
        else:
            self.status.update({"status_message": "Emir gönderilemedi.", "in_position": False})
        
        print(self.status["status_message"])

bot_core = BotCore()

# Not: Bu güncelleme, binance_client.py dosyasında pozisyonu tek bir emirle kapatacak
# yeni bir fonksiyona ihtiyaç duyar. Onu da ekleyelim:
