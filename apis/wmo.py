import os
import requests


def fetch_weather_data(dest_id):
    url = "https://worldweather.wmo.int/en/json/" + str(dest_id) + "_en.json"
    r = requests.get(url=url, params={})
    try:
        result = r.json()
    except:
        return None
    return result["city"]
