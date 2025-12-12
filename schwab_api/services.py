import os
import requests

SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
SCHWAB_CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


def exchange_code_for_token(code):
    url = "https://api.schwab.com/oauth2/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SCHWAB_CLIENT_ID,
        "client_secret": SCHWAB_CLIENT_SECRET
    }

    r = requests.post(url, data=data)
    return r.json()
