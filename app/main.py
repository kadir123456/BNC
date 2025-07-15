import asyncio
import secrets
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .bot_core import bot_core
from .config import settings

# --- Güvenlik ---
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Kullanıcı adı ve şifreyi doğrulamak için bir dependency fonksiyonu.
    Zamanlama saldırılarına karşı korumalı `secrets.compare_digest` kullanır.
    """
    correct_username = secrets.compare_digest(credentials.username, settings.BOT_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.BOT_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre yanlış",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Uygulama Başlatma ---
app = FastAPI(
    title="Binance Futures Kaldıraçlı İşlem Botu",
    description="5 dakikalık grafiklerde sinyal algılayarak otomatik işlem yapan bot.",
    version="1.0.0"  # Tamamlanmış Sürüm
)

@app.on_event("shutdown")
async def shutdown_event():
    if bot_core.status["is_running"]:
        print("Uygulama kapatılıyor, bot durduruluyor...")
        await bot_core.stop()

# --- Veri Modelleri ---
class StartRequest(BaseModel):
    symbol: str

# --- API Endpoint'leri ---

@app.post("/api/start")
async def start_bot(request: StartRequest, background_tasks: BackgroundTasks, username: str = Depends(authenticate)):
    """
    Botu belirtilen coin sembolü için başlatır. (Korumalı)
    """
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
    
    symbol = request.symbol.upper()
    background_tasks.add_task(bot_core.start, symbol)
    await asyncio.sleep(1)
    return bot_core.status

@app.post("/api/stop")
async def stop_bot(username: str = Depends(authenticate)):
    """
    Çalışan botu durdurur. (Korumalı)
    """
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
    
    await bot_core.stop()
    return bot_core.status

@app.get("/api/status")
async def get_status():
    """
    Botun anlık durumunu döndürür. (Herkese Açık)
    """
    return bot_core.status

# --- Frontend Dosyalarını Sunmak ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
