import os
import math
import urllib
import json
import logging
import ssl
import re
import googlemaps
from util.util import list_to_str_no_brackets
import requests
import time

client = googlemaps.Client(key=os.environ["GOOGLE_API_KEY"])

USER_AGENT = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/54.0.2840.98 Safari/537.36"}


def get_poi_details(poi_id):
    details = client.place(poi_id, language="en")
    return details["result"]


def fetch_image_url(ref):
    url = "https://maps.googleapis.com/maps/api/place/photo"
    params = dict(key=os.environ["GOOGLE_API_KEY"],
                  photoreference=ref, maxwidth=10000)
    response = requests.get(url=url, params=params)
    photo = response.url
    return photo


def get_nearby_POIs(latitude, longitude, text_location):
    location = [latitude, longitude]
    all_pois = []
    collected_all = False
    next_page_token = None
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    while not collected_all:
        if next_page_token != None:
            params = dict(
                key=os.environ["GOOGLE_API_KEY"], pagetoken=next_page_token)
            nearby_pois = requests.get(url=url, params=params).json()
        else:
            nearby_pois = client.places_nearby(location=list_to_str_no_brackets(location), keyword='tourist',
                                               language="en", radius=10000)
        all_pois.extend(nearby_pois["results"])
        if "next_page_token" not in nearby_pois:
            collected_all = True
        else:
            next_page_token = nearby_pois["next_page_token"]
            time.sleep(2)

    return all_pois


def get_visit_durations():
    pass
