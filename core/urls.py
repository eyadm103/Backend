# trading_backend/core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_status_view, name='trading_status_api'),
]