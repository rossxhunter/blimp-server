from config import db_manager
from flask.json import jsonify
from util.util import list_to_tuple


def fetch_suggestions(suggestion):
    if suggestion == "destinations":
        return fetch_destination_suggestions()
    elif suggestion == "activities":
        return fetch_activity_suggestions()
    elif suggestion == "currencies":
        return fetch_currency_suggestions()
    elif suggestion == "explore":
        return fetch_explore_suggestions()


def fetch_explore_suggestions():
    dest_names = ["Paris", "Madrid", "London", "New York", "Singapore"]
    suggestions = []
    for name in dest_names:
        suggestions.append({"name": name})
    return jsonify(suggestions)


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
    SELECT name, municipality, iata_code FROM airports WHERE type = "large_airport" AND iata_code IS NOT NULL AND municipality IS NOT NULL
    """)
    airports = []
    for airport in airports_query:
        airports.append(
            {"heading": airport[0], "subheading": airport[1], "type": "airport", "id": airport[2]})

    cities_query = db_manager.query("""
    SELECT id, name, country_code FROM destination WHERE city_code IS NOT NULL
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"heading": city[1], "subheading": city[2], "type": "city", "id": city[0]})

    suggestions = airports + cities
    return jsonify(suggestions)
