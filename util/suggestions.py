from config import dbManager
from flask.json import jsonify


def fetch_suggestions(suggestion):
    if suggestion == "destinations":
        return fetch_destination_suggestions()
    elif suggestion == "activities":
        return fetch_activity_suggestions()


def fetch_activity_suggestions():
    activities_query = dbManager.query("""
    SELECT id, name, icon_prefix FROM categories WHERE culture_score <> 0
    """)
    activities = []
    for activity in activities_query:
        activities.append(
            {"heading": activity[1], "subheading": "", "icon": activity[2], "id": activity[0]})
    print(activities)
    return jsonify(activities)


def fetch_destination_suggestions():
    airports_query = dbManager.query("""
    SELECT name, municipality, iata_code FROM airports WHERE type = "large_airport" AND iata_code IS NOT NULL AND municipality IS NOT NULL
    """)
    airports = []
    for airport in airports_query:
        airports.append(
            {"heading": airport[0], "subheading": airport[1], "type": "airport", "id": airport[2]})

    cities_query = dbManager.query("""
    SELECT id, name, country_code FROM destination WHERE city_code IS NOT NULL
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"heading": city[1], "subheading": city[2], "type": "city", "id": city[0]})

    suggestions = airports + cities
    return jsonify(suggestions)


def is_city_added(cities, airport):
    for city in cities:
        if (city["heading"] == airport[1] and city["subheading"] == airport[2]):
            return True
    return False
