import os
import math
import urllib
import json
import logging
import ssl
import re
import googlemaps

client = googlemaps.Client(key=os.environ["GOOGLE_API_KEY"])

USER_AGENT = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/54.0.2840.98 Safari/537.36"}


def get_google_places(latitude, longitude):

    nearby_places = client.places_nearby(location=(latitude, longitude),
                                         language="en", radius=5000,
                                         type="tourist_attraction", open_now=False)

    # pop_times = get_populartimes_from_search(
    #     "ethos imperial")

    return
