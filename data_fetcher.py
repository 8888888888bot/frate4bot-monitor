import requests
import hmac
import hashlib
import time
from config import GATEIO_API_KEY, GATEIO_SECRET_KEY

BASE_URL = "https://api.gateio.ws/api/v4"

def get_funding_rates():
    endpoint = "/futures/usdt/tickers"
    url = BASE_URL + endpoint
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {item["contract"]: float(item["funding_rate"]) for item in data}
    except Exception as e:
        print(f"[ERROR] Failed to fetch funding rates: {e}")
        return {}

def get_signed_request(method, endpoint, params=None):
    # Not needed for public /tickers endpoint, but kept for extensibility
    pass
