# app/firebase_manager.py

import firebase_admin
from firebase_admin import credentials, db, auth
import os
import json
from datetime import datetime, timezone

class FirebaseManager:
    def __init__(self):
        try:
            cred_json_str = os.getenv("FIREBASE_CREDENTIALS_JSON")
            database_url = os.getenv("FIREBASE_DATABASE_URL")

            if cred_json_str and database_url:
                cred_dict = json.loads(cred_json_str)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {'databaseURL': database_url})
                self.db_ref = db.reference('trades')
                print("Firebase (Admin SDK & Realtime DB) başarıyla başlatıldı.")
            else:
                self.db_ref = None
                print("UYARI: Firebase kimlik bilgileri (JSON veya Database URL) bulunamadı.")
        except Exception as e:
            self.db_ref = None
            print(f"Firebase başlatılırken hata oluştu: {e}")

    def log_trade(self, trade_data: dict):
        """Bir işlemi Realtime Database'e kaydeder."""
        if not self.db_ref:
            print("Veritabanı bağlantısı yok, işlem kaydedilemedi.")
            return
        try:
            # Zaman damgasını string'e çevirerek uyumluluk sağla
            trade_data['timestamp'] = trade_data.get('timestamp').isoformat()
            self.db_ref.push(trade_data) # Yeni bir kayıt eklemek için push() kullanılır
            print(f"--> İşlem başarıyla Firebase Realtime DB'e kaydedildi.")
        except Exception as e:
            print(f"Firebase'e işlem kaydedilirken hata oluştu: {e}")

    def verify_token(self, token: str):
        """Gelen ID Token'ını doğrular ve kullanıcı bilgilerini döndürür."""
        try:
            return auth.verify_id_token(token)
        except Exception as e:
            print(f"Token doğrulama hatası: {e}")
            return None

firebase_manager = FirebaseManager()
