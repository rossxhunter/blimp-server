from config import db_manager
from flask.json import jsonify
from util.util import list_to_str_no_brackets, list_to_tuple
from apis import google_places
import random
import os
from util.db_populate import populate_DB
from datetime import datetime


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
    dests_query = db_manager.query("""
    SELECT destination.id, destination.name 
    FROM external_itinerary
    JOIN destination ON destination.id = external_itinerary.destination_id
    GROUP BY destination.id, destination.name
    """)
    dests = []
    for d in dests_query:
        dests.append({"id": d[0], "name": d[1]})
    return jsonify(dests)


def get_explore_dests(page, origin_id):
    all_dests_query_start = """
    SELECT destination.id, destination.name, destination.country_code, country.Country, flyable_destination.departure_date, flyable_destination.return_date, MIN(flyable_destination.price_amount)
    FROM destination
    JOIN country ON country.ISO = destination.country_code
    JOIN flyable_destination ON flyable_destination.destination = destination.id
    """
    all_dests_query_extra = """
    GROUP BY flyable_destination.destination, flyable_destination.departure_date, flyable_destination.return_date
    ORDER BY destination.tourist_score DESC
    """
    if (page == "For You"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            WHERE tourist_score IS NOT NULL AND flyable_destination.origin = {origin_id}
            """.format(origin_id=origin_id)
            + all_dests_query_extra
        )
    elif (page == "Popular"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            WHERE tourist_score IS NOT NULL AND flyable_destination.origin = {origin_id}
            """.format(origin_id=origin_id) + all_dests_query_extra
        )
    elif (page == "Europe"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            WHERE tourist_score IS NOT NULL AND Continent = "EU" AND flyable_destination.origin = {origin_id}
            """.format(origin_id=origin_id) + all_dests_query_extra
        )
    elif (page == "Asia"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            WHERE tourist_score IS NOT NULL AND Continent = "AS" AND flyable_destination.origin = {origin_id}
            """.format(origin_id=origin_id) + all_dests_query_extra
        )
    elif (page == "Americas"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            WHERE tourist_score IS NOT NULL AND (Continent = "SA" OR Continent = "NA") AND flyable_destination.origin = {origin_id}
            """.format(origin_id=origin_id) + all_dests_query_extra
        )
    return list(dests_query)


def fetch_explore_suggestions():
    pages = ["For You", "Popular", "Europe", "Asia", "Americas"]
    all_suggestions = {}
    for page in pages:
        origin_id = 2643743
        dests = get_explore_dests(page, origin_id)
        dest_map = {}
        for dest in dests:
            dest_map[dest[0]] = dest
        dests = list(dest_map.values())
        if page == "For You":
            dests = dests[:100]
        else:
            dests = dests[:20]
        random.shuffle(dests)
        dests = dests[:10]
        suggestions = []
        dest_images = {}
        valid_dests = []
        for dest in dests:
            images_query = db_manager.query("""
            SELECT url FROM destination_photo
            WHERE dest_id = {dest_id}
            """.format(dest_id=dest[0]))
            if len(images_query) != 0:
                valid_dests.append(dest)
                dest_images[dest[0]] = images_query[0][0]
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
        """.format(dest_ids=list_to_str_no_brackets(list(map(lambda x: x[0], valid_dests)))))
        attractions = {}
        for att in top_attractions_query:
            if att[0] in attractions:
                attractions[att[0]].append(att[1])
            else:
                attractions[att[0]] = [att[1]]
        for d in valid_dests:
            selected_attractions = attractions[d[0]]
            random.shuffle(selected_attractions)
            selected_attractions = selected_attractions[:3]
            suggestions.append(
                {"id": d[0], "name": d[1], "country_code": d[2].lower(), "country_name": d[3], "departure_date": datetime.strftime(d[4], "%Y-%m-%d"), "return_date": datetime.strftime(d[5], "%Y-%m-%d"), "image": dest_images[d[0]], "top_attractions": selected_attractions})
        all_suggestions[page] = suggestions
    return jsonify(all_suggestions)


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
    SELECT id, name, plural_name, icon_prefix FROM categories
    ORDER BY culture_score DESC
    """)
    activities = []
    for activity in activities_query:
        activities.append(
            {"name": activity[1], "plural": activity[2], "icon": activity[3], "id": activity[0]})
    return jsonify(activities)


def fetch_destination_suggestions():
    airports_query = db_manager.query("""
    SELECT airports.name, municipality, iata_code, country_code FROM airports 
    JOIN destination ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
    WHERE iata_code IS NOT NULL AND municipality IS NOT NULL AND tourist_score IS NOT NULL
    """)
    airports = []
    for airport in airports_query:
        airports.append(
            {"airportName": airport[0], "countryCode": airport[3].lower(), "cityName": airport[1], "type": "airport", "id": airport[2]})

    cities_query = db_manager.query("""
    SELECT id, name, country_code, country.Country FROM destination 
    JOIN country ON country.ISO = destination.country_code
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"cityName": city[1], "countryCode": city[2].lower(), "countryName": city[3], "type": "city", "id": city[0]})

    suggestions = airports + cities
    return jsonify(suggestions)
