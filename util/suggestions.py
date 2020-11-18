from config import db_manager
from flask.json import jsonify
from util.util import list_to_str_no_brackets, list_to_tuple
from apis import google_places, osm
import random
import os
from util.db_populate import populate_DB
from datetime import datetime, timedelta
import clicks
import apis.musement as museument


def fetch_all_suggestions():
    populate_DB()
    destinations = fetch_destination_suggestions()
    activities = fetch_activity_suggestions()
    currencies = fetch_currency_suggestions()
    explore = fetch_explore_suggestions()
    attractions = fetch_attraction_suggestions()
    search = fetch_search_suggestions()
    availableFlights = fetch_available_flights()
    testing = fetch_testing_suggestions()
    countries = fetch_countries_suggestions()
    return {"destinations": destinations, "activities": activities, "currencies": currencies, "explore": explore, "attractions": attractions, "search": search, "availableFlights": availableFlights, "testing": testing, "countries": countries}


def fetch_suggestions(suggestion):
    if suggestion == "destinations":
        return fetch_destination_suggestions()
    elif suggestion == "activities":
        return fetch_activity_suggestions()
    elif suggestion == "currencies":
        return fetch_currency_suggestions()
    elif suggestion == "explore":
        return fetch_explore_suggestions()
    elif suggestion == "attractions":
        return fetch_attraction_suggestions()
    elif suggestion == "search":
        return fetch_search_suggestions()
    elif suggestion == "available_flights":
        return fetch_available_flights()
    elif suggestion == "testing":
        return fetch_testing_suggestions()


def fetch_countries_suggestions():
    countries_query = db_manager.query("""
    SELECT ISO, Country
    FROM country
    ORDER BY Country
    """)
    countries = []
    for country in countries_query:
        countries.append({"code": country[0], "name": country[1]})
    return countries


def fetch_available_flights():
    min_date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    max_date = datetime.strftime(
        datetime.now() + timedelta(days=90), "%Y-%m-%d")
    flights_query = db_manager.query("""
    SELECT origin, destination, departure_date, return_date, price_amount, price_currency
    FROM flyable_destination
    WHERE departure_date > "{min_date}" AND departure_date < "{max_date}"
    """.format(min_date=min_date, max_date=max_date))
    flights = []
    for flight in flights_query:
        flights.append({"origin": flight[0], "destination": flight[1], "departureDate": datetime.strftime(flight[2], "%Y-%m-%d"),
                        "returnDate": datetime.strftime(flight[3], "%Y-%m-%d"), "price": {"amount": flight[4], "currency": flight[5]}})
    return flights


def fetch_search_suggestions():
    cities_query = db_manager.query("""
    SELECT id, name, country_code, country.Country FROM destination
    JOIN country ON country.ISO = destination.country_code
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"name": city[1], "countryCode": city[2].lower(), "countryName": city[3], "type": "city", "id": city[0]})

    hotels_query = db_manager.query("""
    SELECT hotel.id, hotel.name, destination.name, destination.country_code, hotel_photo.url 
    FROM hotel
    JOIN destination ON hotel.city = destination.city_code
    JOIN hotel_photo ON hotel_photo.id = (
        SELECT h.id FROM hotel_photo AS h
        WHERE h.hotel_id = hotel.id
        LIMIT 1
    )
    """)
    hotels = []
    for hotel in hotels_query:
        hotels.append(
            {"id": hotel[0], "name": hotel[1], "city": hotel[2], "countryCode": hotel[3], "image": hotel[4]})

    attractions_query = db_manager.query("""
    SELECT poi.id, poi.name, destination.name, categories.name, categories.icon_prefix, destination.country_code, poi_photo.url
    FROM poi
    JOIN categories ON poi.foursquare_category_id = categories.id
    JOIN destination ON destination.id = poi.destination_id
    JOIN poi_photo ON poi_photo.reference = (
        SELECT p.reference FROM poi_photo AS p
        WHERE p.poi_id = poi.id
        LIMIT 1
    )
    WHERE poi.num_ratings > 1000
    """)
    attractions = []
    for attraction in attractions_query:
        attractions.append(
            {"id": attraction[0], "name": attraction[1], "city": attraction[2], "cat_name": attraction[3], "cat_icon": attraction[4], "countryCode": attraction[5], "image": attraction[6]})

    return {"destinations": cities, "hotels": hotels, "attractions": attractions}


def fetch_attraction_suggestions():
    attractions_query = db_manager.query("""
    SELECT poi.id, poi.name, destination.name, country_code, categories.name, categories.icon_prefix, poi_photo.url
    FROM poi
    JOIN categories ON poi.foursquare_category_id = categories.id
    JOIN destination ON destination.id = poi.destination_id
    JOIN poi_photo ON poi_photo.reference = (
        SELECT p.reference FROM poi_photo AS p
        WHERE p.poi_id = poi.id
        LIMIT 1
    )
    ORDER BY poi.num_ratings DESC
    LIMIT 100
    """)
    random_nums = []
    for i in range(0, 15):
        new_added = False
        while not new_added:
            new_random_num = round(random.random() * 99)
            if new_random_num not in random_nums:
                random_nums.append(new_random_num)
                new_added = True

    attractions = []
    for i in range(0, 15):
        attractions.append(
            {"id": attractions_query[random_nums[i]][0], "name": attractions_query[random_nums[i]][1], "city_name": attractions_query[random_nums[i]][2], "country_code": attractions_query[random_nums[i]][3], "cat_name": attractions_query[random_nums[i]][4], "cat_icon": attractions_query[random_nums[i]][5], "photo": attractions_query[random_nums[i]][6]})
    return attractions


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
    return dests


def get_explore_dests(page, origin_id, dest_id=None):
    all_dests_query_start = """
    SELECT destination.id, destination.name, destination.country_code, country.Country, culture_score, shopping_score, nightlife_score
    FROM destination
    JOIN country ON country.ISO = destination.country_code
    WHERE tourist_score IS NOT NULL AND destination.id != {dest_id}
    """.format(dest_id=dest_id)
    all_dests_query_extra = """
    ORDER BY destination.tourist_score DESC
    """
    if (page == "Similar"):
        dests_query = db_manager.query(
            all_dests_query_start
            + all_dests_query_extra
        )
    elif (page == "For You"):
        dests_query = db_manager.query(
            all_dests_query_start
            + all_dests_query_extra
        )
    elif (page == "Popular"):
        dests_query = db_manager.query(
            all_dests_query_start + all_dests_query_extra
        )
    elif (page == "Europe"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            AND Continent = "EU"
            """ + all_dests_query_extra
        )
    elif (page == "Asia"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            AND Continent = "AS"
            """ + all_dests_query_extra
        )
    elif (page == "Americas"):
        dests_query = db_manager.query(
            all_dests_query_start +
            """
            AND (Continent = "SA" OR Continent = "NA")
            """ + all_dests_query_extra
        )
    return list(dests_query)


def fetch_similar_destinations(dest_id):
    origin_id = 2643743
    dests = get_explore_dests("Similar", origin_id, dest_id=dest_id)
    dest_map = {}
    for dest in dests:
        dest_map[dest[0]] = dest
    dests = list(dest_map.values())
    suggestions = []
    dest_images = {}
    for dest in dests:
        images_query = db_manager.query("""
            SELECT url FROM destination_photo
            WHERE dest_id = {dest_id}
            """.format(dest_id=dest[0]))
        if len(images_query) != 0:
            # valid_dests.append(dest)
            dest_images[dest[0]] = []
            for image in images_query:
                dest_images[dest[0]].append(image[0])
    for d in dests:
        suggestions.append(
            {"id": d[0], "name": d[1], "country_code": d[2].lower(), "country_name": d[3], "culture": d[4], "shopping": d[5], "nightlife": d[6], "images": dest_images[d[0]]})
    return suggestions


def fetch_explore_suggestions():
    pages = ["For You", "Popular", "Europe", "Asia", "Americas"]
    all_suggestions = {}
    for page in pages:
        origin_id = 2643743
        dests = get_explore_dests(page, origin_id, dest_id=origin_id)
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
                dest_images[dest[0]] = []
                for image in images_query:
                    dest_images[dest[0]].append(image[0])
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
                {"id": d[0], "name": d[1], "country_code": d[2].lower(), "country_name": d[3], "culture": d[4], "shopping": d[5], "nightlife": d[6], "images": dest_images[d[0]], "top_attractions": selected_attractions})
        all_suggestions[page] = suggestions
    return all_suggestions


def fetch_currency_suggestions():
    accepted_currencies = ["GBP", "USD", "EUR"]
    currencies_query = db_manager.query("""
    SELECT id, name, symbol FROM currency WHERE id IN {accepted_currencies}
    """.format(accepted_currencies=list_to_tuple(accepted_currencies)))
    currencies = {}
    for currency in currencies_query:
        currencies[currency[0]] = {"name": currency[1], "symbol": currency[2]}
    return currencies


def fetch_activity_suggestions():
    activities_query = db_manager.query("""
    SELECT id, name, plural_name, icon_prefix FROM categories
    ORDER BY culture_score DESC
    """)
    activities = []
    for activity in activities_query:
        activities.append(
            {"name": activity[1], "plural": activity[2], "icon": activity[3], "id": activity[0]})
    return activities


def fetch_destination_suggestions():
    airports_query = db_manager.query("""
    SELECT airports.name, municipality, iata_code, country_code, destination.id FROM airports 
    JOIN destination ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
    WHERE iata_code IS NOT NULL AND municipality IS NOT NULL AND tourist_score IS NOT NULL
    """)
    airports = []
    for airport in airports_query:
        airports.append(
            {"airportName": airport[0], "countryCode": airport[3].lower(), "cityName": airport[1], "type": "airport", "id": airport[2], "cityId": airport[4]})

    cities_query = db_manager.query("""
    SELECT id, name, country_code, country.Country FROM destination 
    JOIN country ON country.ISO = destination.country_code
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL
    ORDER BY tourist_score DESC
    """)
    cities = []
    for city in cities_query:
        cities.append(
            {"cityName": city[1], "countryCode": city[2].lower(), "countryName": city[3], "type": "city", "id": city[0]})

    suggestions = cities + airports
    return suggestions
