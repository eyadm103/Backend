# trading_backend/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv # 🚨 1. استيراد dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 🚨 2. تحميل متغيرات البيئة من ملف .env (نفترض أنه في المجلد الأب TradingApp/Backend/)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 🚨 3. استخدام os.getenv لقراءة المفتاح السري (مفضل لأمان أكبر)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-@e^z_!s7a$z6v_7-e43&x6q5b-25@5w5$k3&o+q5)z#r-1(z*^')
DEBUG = os.getenv("DEBUG", "True") == "True" # 🚨 4. قراءة DEBUG من .env
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(',') # 🚨 5. قراءة ALLOWED_HOSTS من .env

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'schwab_api', # ✅ موجودة بالفعل
    
]

# ... (باقي كود MIDDLEWARE, TEMPLATES, DATABASES كما هو)

# ... (جزء API Keys الأخرى - تركناها كما هي)

# 🚨 6. إضافة متغيرات شواب والأمان (يجب أن تقرأ من .env)
# تأكد من أن هذه الأسماء مطابقة لما وضعته في ملف .env
SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
SCHWAB_CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET")
SCHWAB_REDIRECT_URI = os.getenv("REDIRECT_URI") # تم تغيير الاسم ليكون أوضح
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")


# ... (باقي الإعدادات كما هي: API_KEY, API_SECRET, BASE_URL, GLOBAL_STOCK_TICKER, إلخ)


# trading_backend/settings.py

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-@e^z_!s7a$z6v_7-e43&x6q5b-25@5w5$k3&o+q5)z#r-1(z*^'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'schwab_api',
    

]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'trading_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'trading_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
CORS_ALLOW_ALL_ORIGINS = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'  
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
API_KEY = os.getenv('APCA_API_KEY_ID', 'PKJAKXWLFBRV2EJYP5OM72I6ZW')
API_SECRET = os.getenv('APCA_API_SECRET_KEY', 'HZDX9TQQKx2ATv7g1VeECyZDqNCJDTFdBtF3C7XwaH1M')
BASE_URL = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets') # For paper trading

GLOBAL_STOCK_TICKER = 'NVDA'
MAX_EQUITY_PER_TRADE = 0.80
RISK_PER_TRADE_PERCENT = 0.006
SL_MULTIPLIER = 1
TP_MULTIPLIER = 2
MAX_TRADES_PER_DAY = 55
MAX_DAILY_LOSS_PERCENT = 0.10

MODELS_DIR = os.path.join(BASE_DIR, 'core/model')
MODEL_FILENAME = 'final_model.pkl' 
MODEL_FEATURE_NAMES = [
    'macd_line', 'macd_signal', 'macd_diff', 'bb_hband', 'bb_lband', 'bb_wband',
    'sma_20', 'rsi_14', 'atr_14', 'daily_range_pct', 'volatility_5_std',
    'volatility_20_std', 'year', 'month', 'dayofweek',
    'lag_1_close_return', 'lag_5_close_return', 'lag_20_close_return',
    'gap_open_close_prev_pct',
    'volume', 'high_low_spread', 'open_close_spread', 'momentum_10d', 'volume_change_pct'
]

TRADING_LOG_FILE = 'trading_log.txt'
DAILY_PERFORMANCE_FILE = 'daily_performance.csv'
STATUS_JSON_FILE = 'trading_status.json'
