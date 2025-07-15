from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio

# Gerçek bot mantığını ve durumunu import ediyoruz
from .bot_core import bot_core

# --- Uygulama Başlatma ---
app = FastAPI(
    title="Binance Futures Kaldıraçlı İşlem Botu",
    description="5 dakikalık grafiklerde sinyal algılayarak otomatik işlem yapan bot.",
    version="0.2.0" # Sürümü güncelleyelim
)

# --- FastAPI Yaşam Döngüsü Olayları ---
@app.on_event("shutdown")
async def shutdown_event():
    """
    Uygulama kapatıldığında (örn: Render.com'da yeniden başlatma) botu güvenle durdur.
    """
    if bot_core.status["is_running"]:
        print("Uygulama kapatılıyor, bot durduruluyor...")
        await bot_core.stop()

# --- Veri Modelleri ---
class StartRequest(BaseModel):
    symbol: str

# --- API Endpoint'leri ---

@app.post("/api/start")
async def start_bot(request: StartRequest, background_tasks: BackgroundTasks):
    """
    Botu belirtilen coin sembolü için bir arka plan görevinde başlatır.
    """
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")

    symbol = request.symbol.upper()
    
    # bot_core.start fonksiyonunu arka planda çalıştır.
    # Bu sayede API isteği hemen yanıt döner ve bot arkada çalışmaya devam eder.
    background_tasks.add_task(bot_core.start, symbol)
    
    # Başlatma mesajını hemen döndür, botun durumu daha sonra /api/status'tan takip edilecek.
    await asyncio.sleep(1) # bot_core'un başlangıç durumunu ayarlaması için kısa bir bekleme
    return bot_core.status


@app.post("/api/stop")
async def stop_bot():
    """
    Çalışan botu durdurur.
    """
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")

    await bot_core.stop()
    return bot_core.status


@app.get("/api/status")
async def get_status():
    """
    Botun anlık durumunu döndürür. Arayüz bu endpoint'i periyodik olarak çağırır.
    """
    return bot_core.status


# --- Frontend Dosyalarını Sunmak ---
# StaticFiles'ı kök dizine bağlayarak index.html'in ana URL'de sunulmasını sağlıyoruz.
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """
    Kök URL'ye gelen isteklerde index.html dosyasını döndürür.
    """
    return FileResponse('static/index.html')