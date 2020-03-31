import requests


def get_exchange_rate(base, target):
    url = "https://api.exchangeratesapi.io/latest"
    params = {"base": base, "symbols": target}
    r = requests.get(url=url, params=params)
    data = r.json()
    return data["rates"][target]
