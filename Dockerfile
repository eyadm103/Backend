# استخدام صورة Miniconda/Miniforge وهي مثالية للمشاريع العلمية و ML
# هذه الصورة تحتوي على جميع مكتبات النظام المطلوبة لـ lightgbm و numpy
FROM mambaorg/miniforge3:23.11.0-1

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف متطلبات بايثون
COPY requirements.txt .

# تثبيت المكتبات باستخدام pip
# (Miniforge يأتي مع pip)
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع (بما في ذلك المودل في core/model)
COPY . .

# تعريف المنفذ
EXPOSE 8080

# تحديد أمر البدء الافتراضي (سيعمل كاحتياطي للـ Custom Start Command)
CMD ["gunicorn", "trading_backend.wsgi:application", "--bind", "0.0.0.0:8080"]