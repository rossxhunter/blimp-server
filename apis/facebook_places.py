import requests
import csv
from util.util import list_to_str_no_brackets


def search_facebook_place(name, latitude, longitude):
    keys_csv = open("facebook_keys.csv")
    csv_reader = csv.reader(keys_csv, delimiter=',')
    keys = []
    for row in csv_reader:
        keys.append(row[0] + "|" + row[1])
    success = False
    i = 0
    while success == False:
        access_token = keys[i]
        url = "https://graph.facebook.com/search"
        fields_list = ["name", "checkins", "cover", "about", "description",
                       "hours", "overall_star_rating", "single_line_address", "website", "phone", "link", "category_list"]
        center = [latitude, longitude]
        params = {"access_token": access_token, "type": "place", "q": name,
                  "fields": list_to_str_no_brackets(fields_list), "center": list_to_str_no_brackets(center)}
        r = requests.get(url=url, params=params).json()
        if "error" not in r:
            success = True
            pois = r["data"]
            if len(pois) == 0:
                return None
        elif r["error"]["code"] == 4:
            if i == len(keys) - 1:
                i = 1
            else:
                i += 1
        else:
            return None
    return pois[0]
