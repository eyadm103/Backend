from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.schwab_login, name='schwab_login'),      # توليد رابط OAuth
    path('callback/', views.schwab_callback, name='schwab_callback'),  # استقبال التوكن
]
