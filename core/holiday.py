from config import db_manager
from core.itinerary import calculate_itinerary, get_POIs_for_destination
from flask import json, jsonify
from apis import amadeus
from core.destination import calculate_destination
from core import accommodation, flights
from util.util import get_origin_code
from util.db_populate import populate_DB


def get_holiday(constraints, soft_prefs, pref_scores, feedback=None):
    destination = calculate_destination(
        constraints, soft_prefs, pref_scores, feedback)

    dest_code_query = db_manager.query("""
    SELECT city_code FROM destination WHERE id={dest_id}
    """.format(dest_id=destination["id"]))

    city_id = dest_code_query[0][0]

    dest_id_for_travel = city_id

    if "destination" in constraints:
        if constraints["destination"]["type"] == "airport":
            dest_id_for_travel = constraints["destination"]["id"]

    origin_code = get_origin_code(constraints["origin"])

    accommodation_options = destination["accommodation"]

    travel_options = destination["flights"]

    accommodation_options.sort(
        key=get_accommodation_score, reverse=True)

    travel, accommodation = choose_travel_and_accommodation(
        travel_options, accommodation_options, constraints["budget_leq"], feedback)

    pois = get_POIs_for_destination(destination["id"], pref_scores)
    itinerary = calculate_itinerary(
        dict(pois), travel, accommodation, constraints, soft_prefs, pref_scores)

    pois_list = get_pois_list(pois)

    return json.dumps(dict(name=destination["name"], weather={"temp": destination["av_temp_c"], "rainfall": destination["num_days_rainfall"]}, countryInfo={"countryCode": destination["country_code"], "countryName": destination["country_name"]}, wiki=destination["wiki"], imageURLs=destination["image_urls"], destId=destination["id"], itinerary=itinerary, travel=travel, accommodation=accommodation, all_travel=travel_options, all_accommodation=accommodation_options, all_activities=pois_list))


def get_pois_list(pois):
    poi_items = pois.items()
    l = []
    for poi_item in poi_items:
        m = poi_item[1]
        m["id"] = poi_item[0]
        l.append(m)
    return l


def get_accommodation_score(acc):
    return acc["stars"]


def choose_travel_and_accommodation(travel_options, ranked_accommodation_options, budget, feedback):
    maximum_price = budget
    if feedback != None and feedback["type"] == "cheaper":
        maximum_price = min(budget, feedback["previous_price"])

    for acc in ranked_accommodation_options:
        if travel_options[0]["price"]["amount"] + acc["price"]["amount"] < maximum_price:
            return (travel_options[0], acc)
