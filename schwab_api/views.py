from django.http import JsonResponse
from cryptography.fernet import Fernet
import requests
import os
from .models import SchwabToken

# قراءة المتغيرات من .env
CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI") 
CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET")  # يمكن عدم استخدامها إذا مش مطلوبة

# ====== Function لتحويل code لتوكن ======
def exchange_code_for_token(code):
    url = "https://api.schwab.com/oauth2/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
    }

    try:
        response = requests.post(
            url,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {
            "error": "Token exchange failed",
            "details": str(e),
            "response_text": response.text if 'response' in locals() else "No response"
        }

# ====== Callback URL ======
def schwab_callback(request):
    code = request.GET.get('code')

    if not code:
        return JsonResponse({"status":"error", "message": "No authorization code provided."}, status=400)

    token_data = exchange_code_for_token(code)

    if "error" in token_data:
        return JsonResponse({"status":"error", "message": "Failed to get tokens.", "details": token_data}, status=500)

    try:
        SchwabToken.create_or_update_from_data(token_data)
        return JsonResponse({"status": "success", "message": "Tokens exchanged and stored securely."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": "Failed to store token.", "details": str(e)}, status=500)

# ====== Login URL ======
def schwab_login(request):
    auth_url = (
        "https://api.schwab.com/oauth2/authorize?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}"
    )
    return JsonResponse({"login_url": auth_url})
