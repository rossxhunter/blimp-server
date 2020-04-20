import os
import requests


def fetch_images(destinations):
    key = os.environ["PIXABAY_KEY"]
    url = "https://pixabay.com/api/"
    dest_image_urls = []
    for dest_id, dest_name in destinations:
        params = {"key": key, "q": dest_name, "category": "places"}
        r = requests.get(url=url, params=params)
        result = r.json()
        if (len(result["hits"]) != 0):
            dest_image_urls.append(
                (dest_id, result["hits"][0]["largeImageURL"]))
    return dest_image_urls
