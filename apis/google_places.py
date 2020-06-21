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
import populartimes

client = googlemaps.Client(key=os.environ["GOOGLE_API_KEY"])

USER_AGENT = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/54.0.2840.98 Safari/537.36"}


def get_pop_times():
    pop_times = populartimes.get_id(os.environ["GOOGLE_API_KEY"],
                                    "ChIJPy8Y5kIFdkgRxGSXw4Xjt3s")
    print(pop_times)


def fetch_images(google_id):
    details = client.place(google_id, language="en", fields=["photo"])
    return details["result"]["photos"]


def get_hotel_id(name, lat, lng):
    result = client.find_place(
        name,
        "textquery",
        location_bias="point:{lat},{lng}".format(
            lat=lat, lng=lng),
        language="en",
    )
    if len(result["candidates"]) == 0:
        return None
    return result["candidates"][0]["place_id"]


def fetch_dest_id(dest):
    result = client.find_place(
        dest[1],
        "textquery",
        fields=["place_id"],
        location_bias="point:{lat},{lng}".format(
            lat=dest[2], lng=dest[3]),
        language="en",
    )
    return result["candidates"][0]["place_id"]


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


def get_nearby_POIs(latitude, longitude, lang):
    location = [latitude, longitude]
    all_pois = []
    collected_all = False
    next_page_token = None
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    while not collected_all:
        if next_page_token != None:
            params = dict(
                key=os.environ["GOOGLE_API_KEY"], pagetoken=next_page_token)
            nearby_pois = requests.get(url=url, params=params).json()
        else:
            nearby_pois = client.places_nearby(location=list_to_str_no_brackets(location), keyword='tourist',
                                               language=lang, radius=10000)
        all_pois.extend(nearby_pois["results"])
        if "next_page_token" not in nearby_pois:
            collected_all = True
        else:
            next_page_token = nearby_pois["next_page_token"]
            time.sleep(2)

    return all_pois


def get_visit_durations():
    pass


def search_for_POI(query, latitude, longitude):
    result = client.find_place(
        query,
        "textquery",
        fields=["place_id", "name", "photos",
                "types", "rating", "user_ratings_total", "geometry"],
        location_bias="point:{lat},{lng}".format(
            lat=latitude, lng=longitude),
        language="en",
    )
    return result["candidates"][0]
