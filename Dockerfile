# استخدام صورة Miniconda الرسمية والتي تحتوي على البيئة العلمية المطلوبة
FROM continuumio/miniconda3:latest

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف متطلبات بايثون
COPY requirements.txt .

# تثبيت المكتبات باستخدام pip
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع (بما في ذلك المودل)
COPY . .

# تعريف المنفذ
EXPOSE 8080

# تحديد أمر البدء الافتراضي (لضمان تشغيل الروبوت والخادم عبر Custom Command)
CMD ["gunicorn", "trading_backend.wsgi:application", "--bind", "0.0.0.0:8080"]