import json
import requests
import os
from util.util import list_to_str_no_brackets

base_url = 'https://api.foursquare.com/v2/venues/'
client_id = os.environ["FOURSQUARE_CLIENT_ID"],
client_secret = os.environ["FOURSQUARE_CLIENT_SECRET"]
v = '20200426'


def get_nearby_POIs(city, query):
    params = dict(
        client_id=client_id,
        client_secret=client_secret,
        v=v,
        near=city,
        locale="en",
        # section="sights",
        query=query,
        sortByPopularity=1,
        limit=1000
    )
    resp = requests.get(url=base_url+'explore', params=params)
    data = json.loads(resp.text)
    return data


def get_POI_match(name, latitude, longitude, near):
    params = dict(
        client_id=client_id,
        client_secret=client_secret,
        v=v,
        locale="en",
        # intent="browse",
        # radius=1000,
        # ll=list_to_str_no_brackets([latitude, longitude]),
        near=near,
        # name=name,
        # sortByPopularity=1,
        query=name,
        # address="210弄 Taikang Rd, Da Pu Qiao, Huangpu, China"
    )
    resp = requests.get(url=base_url+'explore', params=params)
    data = json.loads(resp.text)
    if "groups" not in data["response"]:
        return None
    return data["response"]["groups"][0]["items"]


def get_POI_details(id):
    params = dict(
        client_id=client_id,
        client_secret=client_secret,
        v=v,
        locale="en",
    )
    resp = requests.get(url=base_url + id, params=params)
    data = json.loads(resp.text)
    return data


def getCategories():
    params = dict(
        client_id=client_id,
        client_secret=client_secret,
        v=v
    )
    resp = requests.get(url=base_url+'categories', params=params)
    data = json.loads(resp.text)
    return data["response"]["categories"]


def catsToCSV():
    cats = getCategories()
    csv = catsToCSVHelper(cats, [], "null")
    f = open("catagories.txt", "w")
    for line in csv:
        f.write(line.encode('utf8') + '\n')
    f.close()


def catsToCSVHelper(cats, csv, parent):
    for cat in cats:
        csv.append(cat["id"] + "," + cat["name"] + "," + cat["pluralName"] + "," +
                   cat["shortName"] + "," + cat["icon"]["prefix"] + "," + cat["icon"]["suffix"] + "," + parent)
        catsToCSVHelper(cat["categories"], csv, cat["id"])
    return csv
