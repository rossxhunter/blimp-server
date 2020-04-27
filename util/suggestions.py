from config import db_manager
from flask.json import jsonify
from util.util import list_to_str_no_brackets, list_to_tuple
from apis import google_places
import random
import os
from util.db_populate import populate_DB


def fetch_suggestions(suggestion):
    if suggestion == "destinations":
        populate_DB()
        return fetch_destination_suggestions()
    elif suggestion == "activities":
        return fetch_activity_suggestions()
    elif suggestion == "currencies":
        return fetch_currency_suggestions()
    elif suggestion == "explore":
        return fetch_explore_suggestions()
    elif suggestion == "testing":
        return fetch_testing_suggestions()


def fetch_testing_suggestions():
    dest_ids = [3530597, 3435910, 1273294, 745044, 1796236]
    dests_query = db_manager.query("""
    SELECT id, name FROM destination 
    WHERE id IN ({dest_ids})
    """.format(dest_ids=list_to_str_no_brackets(dest_ids)))
    dests = []
    for d in dests_query:
        dests.append({"id": d[0], "name": d[1]})
    return jsonify(dests)


def fetch_explore_suggestions():
    dests_query = db_manager.query("""
    SELECT destination.id, destination.name, destination.country_code, country.Country
    FROM destination
    JOIN country ON country.ISO = destination.country_code
    WHERE tourist_score IS NOT NULL
    ORDER BY destination.tourist_score DESC
    LIMIT 8
    """)
    dests = list(dests_query)
    dests = get_present_dest_images(dests)
    random.shuffle(dests)
    suggestions = []
    dests = dests[:8]
    top_attractions_query = db_manager.query("""
    SELECT ranked.id, ranked.name
    FROM
        (SELECT dests.id, poi.name, RANK() OVER (PARTITION BY dests.id ORDER BY poi.num_ratings DESC) AS rnk
        FROM
            (SELECT id, name, country_code
            FROM destination
            WHERE id IN ({dest_ids})) as dests
        JOIN poi ON poi.destination_id = dests.id) as ranked
    WHERE rnk <= 10
    """.format(dest_ids=list_to_str_no_brackets(list(map(lambda x: x[0], dests)))))
    attractions = {}
    for att in top_attractions_query:
        if att[0] in attractions:
            attractions[att[0]].append(att[1])
        else:
            attractions[att[0]] = [att[1]]
    for d in dests:
        selected_attractions = attractions[d[0]]
        random.shuffle(selected_attractions)
        selected_attractions = selected_attractions[:3]
        suggestions.append(
            {"id": d[0], "name": d[1], "country_code": d[2].lower(), "country_name": d[3], "top_attractions": selected_attractions})
    return jsonify(suggestions)


def get_present_dest_images(dests):
    present = []
    for dest in dests:
        if os.path.isdir("assets/images/destinations/" + str(dest[0])):
            present.append(dest)
    return present


def fetch_currency_suggestions():
    accepted_currencies = ["GBP", "USD", "EUR"]
    currencies_query = db_manager.query("""
    SELECT id, name, symbol FROM currency WHERE id IN {accepted_currencies}
    """.format(accepted_currencies=list_to_tuple(accepted_currencies)))
    currencies = {}
    for currency in currencies_query:
        currencies[currency[0]] = {"name": currency[1], "symbol": currency[2]}
    return jsonify(currencies)


def fetch_activity_suggestions():
    activities_query = db_manager.query("""
    SELECT id, name, icon_prefix FROM categories WHERE culture_score <> 0
    """)
    activities = []
    for activity in activities_query:
        activities.append(
            {"heading": activity[1], "subheading": "", "icon": activity[2], "id": activity[0]})
    return jsonify(activities)


def fetch_destination_suggestions():
    airports_query = db_manager.query("""
    SELECT airports.name, municipality, iata_code FROM airports 
    JOIN destination ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
    WHERE iata_code IS NOT NULL AND municipality IS NOT NULL AND tourist_score IS NOT NULL
    """)
    airports = []
    for airport in airports_query:
        airports.append(
            {"heading": airport[0], "subheading": airport[1], "type": "airport", "id": airport[2]})

    cities_query = db_manager.query("""
    SELECT id, name, country_code FROM destination 
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"heading": city[1], "subheading": city[2], "type": "city", "id": city[0]})

    suggestions = airports + cities
    return jsonify(suggestions)
