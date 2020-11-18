import requests

base_url = "https://api.musement.com/api/v3/"
version = '3.5.0'


def get_venues(city_id):
    headers = {'X-Musement-Version': version}
    new_venues = None
    venues = []
    offset = 0
    limit = 100
    while new_venues != []:
        r = requests.get(url=base_url+"cities/"+str(city_id) + "/venues",
                         params={"offset": offset, "limit": limit}, headers=headers)
        new_venues = r.json()
        venues.extend(new_venues)
        offset += limit
    return venues


def get_cities():
    headers = {'X-Musement-Version': version}
    new_cities = None
    cities = []
    offset = 0
    limit = 100
    while new_cities != []:
        r = requests.get(url=base_url+"cities",
                         headers=headers, params={"offset": offset, "limit": limit, "without_events": "yes"})
        new_cities = r.json()
        cities.extend(new_cities)
        offset += limit
    return cities


def get_activity(activity_id, currency):
    headers = {'X-Musement-Version': version, 'X-Musement-Currency': currency}
    r = requests.get(url=base_url+"activities/"+activity_id, headers=headers)
    activity = r.json()
    return activity


def get_activities_for_venue(venue_id, currency):
    headers = {'X-Musement-Version': version, 'X-Musement-Currency': currency}
    activities = []
    new_activities = None
    offset = 0
    limit = 100
    while new_activities != []:
        r = requests.get(url=base_url+"venues/"+str(venue_id) +
                         "/activities", params={"offset": offset, "limit": limit, "sort_by": "rating"}, headers=headers)
        new_activities = r.json()
        activities.extend(new_activities)
        offset += limit
    return activities


def get_activities(city_id, currency):
    headers = {'X-Musement-Version': version, 'X-Musement-Currency': currency}
    activities = []
    new_activities = None
    offset = 0
    limit = 100
    while new_activities != []:
        r = requests.get(url=base_url+"cities/"+str(city_id) +
                         "/activities", params={"offset": offset, "limit": limit, "sort_by": "relevance"}, headers=headers)
        new_activities = r.json()["data"]
        activities.extend(new_activities)
        offset += limit
    return activities


def get_images(activity_id):
    headers = {'X-Musement-Version': version}
    images = []
    r = requests.get(url=base_url+"activities/"+activity_id +
                     "/media", headers=headers)
    raw_images = r.json()
    for image in raw_images:
        if image["type"] == "image":
            images.append(image["url"])
    return images


def authenticate():
    r = requests.post(url=base_url+"login", params={
        "grant_type": "client_credentials"})
    return r.json()
