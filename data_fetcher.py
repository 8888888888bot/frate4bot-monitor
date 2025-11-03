import requests

def get_funding_rates():
    try:
        r = requests.get("https://api.gateio.ws/api/v4/futures/usdt/contracts", timeout=10)
        r.raise_for_status()
        data = r.json()
        return {item["name"]: {"rate": float(item["funding_rate"])} for item in data if item["name"].endswith("_USDT")}
    except Exception:
        return {}
