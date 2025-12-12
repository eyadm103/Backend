from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome! Use /schwab/login/ to start.")

urlpatterns = [
    path('', home),  # root page
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('schwab/', include('schwab_api.urls')),
]
