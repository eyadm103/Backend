# استخدام صورة بايثون الرسمية
FROM python:3.13.11-slim

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف متطلبات بايثون
COPY requirements.txt .

# تثبيت مكتبات النظام المفقودة (libgomp1) ثم تثبيت مكتبات بايثون
RUN apt-get update && \
    apt-get install -y libgomp1 && \
    pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# تعريف المنفذ
EXPOSE 8080

# تحديد أمر البدء الافتراضي (سيعمل كاحتياطي للـ Custom Start Command)
CMD ["gunicorn", "trading_backend.wsgi:application", "--bind", "0.0.0.0:8080"]