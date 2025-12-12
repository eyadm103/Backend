# schwab_api/security.py
from cryptography.fernet import Fernet
import os

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", None)

FERNET = None
if ENCRYPTION_KEY:
    try:
        # يجب أن يكون المفتاح Base64-encoded 32-byte key
        FERNET = Fernet(ENCRYPTION_KEY.encode()) 
    except ValueError:
        print("ERROR: Invalid Fernet key format in .env.")

def encrypt_token(token_str):
    if not FERNET:
        return token_str 
    # تشفير ثم فك تشفير البايتات إلى string للتخزين في قاعدة البيانات
    return FERNET.encrypt(token_str.encode()).decode()

def decrypt_token(encrypted_token):
    if not FERNET:
        return encrypted_token
    try:
        # تشفير الـ string مرة أخرى إلى بايتات قبل فك التشفير
        return FERNET.decrypt(encrypted_token.encode()).decode()
    except Exception:
         # في حالة وجود خطأ في فك التشفير (ربما تم التخزين بدون تشفير)
         return encrypted_token