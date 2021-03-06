from config import db_manager
from apis import foursquare, wikipedia, google_places, pixabay, wmo, geonames, amadeus, musement
from core import flights, accommodation, itinerary
import urllib
import shutil
import os
import requests
import math
from geopy import distance
from util.city_boundaries import get_city_zones, poi_in_boundaries
from datetime import datetime, timedelta
import re


def populate_DB():
    # add_codes()
    # add_missing_POIs_from_external_itineraries()

    # ADD POI DETAILS
    # populate_POI_table()
    # add_original_names()
    # populate_POI_wiki_desc()
    # fetch_POI_image_urls()
    # populate_foursquare_POI_details()
    # populate_facebook_POI_details()
    # populate_travel_times()

    # ADD DEST DETAILS
    # calculate_tourist_scores()
    # populate_destination_images()
    # fetch_dest_image_urls()
    # populate_dest_wiki()
    # populate_weather_ids()

    # populate_weather_stations()
    # populate_weather_data()

    # populate_flyable_dests()
    # populate_hotels()
    # populate_hotel_images()
    # populate_hotel_ratings()
    # fetch_hotel_image_urls()

    # populate_musement_city_ids()
    # populate_musement_poi_ids()

    # OLD calculate_destination_scores()
    return


def populate_musement_poi_ids():
    cities_query = db_manager.query("""
    SELECT id, musement_id
    FROM destination
    WHERE musement_id IS NOT NULL
    """)
    for city in cities_query:
        musement_city_id = city[1]
        destination_id = city[0]
        venues = musement.get_venues(musement_city_id)
        pois_query = db_manager.query("""
        SELECT id, latitude, longitude
        FROM poi
        WHERE destination_id = {destination_id}
        """.format(destination_id=destination_id))
        matched_pois = []
        for venue in venues:
            for poi in pois_query:
                d = distance.distance(
                    (venue["latitude"], venue["longitude"]), (poi[1], poi[2])).km
                if d < 0.01:
                    matched_pois.append((poi[0], venue["id"]))
        for poi in matched_pois:
            db_manager.insert("""
            UPDATE poi
            SET musement_id = {musement_id}
            WHERE id = "{poi_id}"
            """.format(musement_id=poi[1], poi_id=poi[0]))


def populate_musement_city_ids():
    cities = musement.get_cities()
    for city in cities:
        db_manager.insert("""
        UPDATE destination
        SET musement_id = {musement_id}
        WHERE name = "{city_name}"
        AND tourist_score IS NOT NULL
        """.format(musement_id=city["id"], city_name=city["name"]))


def populate_travel_times():
    dests_query = db_manager.query("""
    SELECT id, latitude, longitude FROM destination
    WHERE tourist_score IS NOT NULL
    """)
    for dest in dests_query:
        start_node = (str(dest[0]), {"is_start": True,
                                     "latitude": dest[1], "longitude": dest[2], "score": 0, "popularity": 0, "rating": 0})
        pois, max_popularity = itinerary.get_POIs_for_destination(
            dest[0], {}, False)
        itinerary.get_durations(pois, start_node)


def fetch_hotel_image_urls():
    photo_query = db_manager.query("""
    SELECT reference, url FROM hotel_photo
    WHERE url IS NULL
    """)
    for photo in photo_query:
        url = google_places.fetch_image_url(photo[0])
        db_manager.insert("""
        UPDATE hotel_photo SET url = "{url}"
        WHERE reference = "{reference}"
        """.format(url=url, reference=photo[0]))


def populate_hotel_images():
    hotel_query = db_manager.query("""
    SELECT id
    FROM hotel
    WHERE images_fetched = 0
    """)
    for hotel in hotel_query:
        h = amadeus.get_accommodation_images(hotel[0])
        if h != None and "media" in h:
            images = h["media"]
            for image in images:
                url = image["uri"].replace("http://", "https://")
                s = re.search('cloudfront.net/(.*)/', url)
                if s != None:
                    url = url.replace("B.JPEG", s.group(1) + ".JPEG")
                db_manager.insert("""
                INSERT INTO hotel_photo (hotel_id, url, type)
                VALUES ("{hotel_id}", "{url}", "{type}")
                """.format(hotel_id=hotel[0], url=url, type=image["category"]))
            db_manager.insert("""
            UPDATE hotel
            SET images_fetched = 1
            WHERE id = "{hotel_id}"
            """.format(hotel_id=hotel[0]))
        else:
            db_manager.insert("""
            UPDATE hotel
            SET images_fetched = NULL
            WHERE id = "{hotel_id}"
            """.format(hotel_id=hotel[0]))


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def populate_hotel_ratings():
    hotel_query = db_manager.query("""
    SELECT id
    FROM hotel
    WHERE ratings_fetched = 0
    LIMIT 100
    """)
    hotels = chunks(hotel_query, 3)
    for hotel_group in hotels:
        hotel_ids = []
        for h in hotel_group:
            hotel_ids.append(h[0])
        res = amadeus.get_accommodation_ratings(hotel_ids)
        ratings = []
        if "data" in res:
            ratings = res["data"]
            for rating in ratings:
                if "sentiments" in rating:
                    db_manager.insert("""
                    INSERT INTO hotel_rating (hotel, overall, sleep_quality, service, facilities, room_comforts, value_for_money, catering, swimming_pool, location, internet, points_of_interest, staff)
                    VALUES ("{hotel_id}", {overall}, {sleep_quality}, {service}, {facilities}, {room_comforts}, {value_for_money}, {catering}, {swimming_pool}, {location}, {internet}, {points_of_interest}, {staff})
                    """.format(hotel_id=rating["hotelId"], overall=rating["overallRating"], sleep_quality=rating["sentiments"]["sleepQuality"] if "sleepQuality" in rating["sentiments"] else "NULL", swimming_pool=rating["sentiments"]["swimmingPool"] if "swimmingPool" in rating["sentiments"] else "NULL", service=rating["sentiments"]["service"] if "service" in rating["sentiments"] else "NULL", facilities=rating["sentiments"]["facilities"] if "facilities" in rating["sentiments"] else "NULL", room_comforts=rating["sentiments"]["roomComforts"], value_for_money=rating["sentiments"]["valueForMoney"] if "valueForMoney" in rating["sentiments"] else "NULL", catering=rating["sentiments"]["catering"], location=rating["sentiments"]["location"], points_of_interest=rating["sentiments"]["pointsOfInterest"], staff=rating["sentiments"]["staff"] if "staff" in rating["sentiments"] else "NULL", internet=rating["sentiments"]["internet"] if "internet" in rating["sentiments"] else "NULL"))
                db_manager.insert("""
                UPDATE hotel
                SET ratings_fetched = 1
                WHERE id = "{hotel_id}"
                """.format(hotel_id=rating["hotelId"]))
        for h_id in hotel_ids:
            if h_id not in ratings:
                db_manager.insert("""
                UPDATE hotel
                SET ratings_fetched = NULL
                WHERE id = "{hotel_id}"
                """.format(hotel_id=h_id))


def populate_hotels():
    dests_query = db_manager.query("""
    SELECT id, city_code FROM destination
    WHERE tourist_score IS NOT NULL
    ORDER BY tourist_score DESC
    LIMIT 10
    """)
    check_in_date = "2020-08-27"
    check_out_date = "2020-08-30"
    for dest in dests_query:
        hotels_already_added_query = db_manager.query("""
        SELECT id FROM hotel WHERE destination_id = {destination_id}
        """.format(destination_id=dest[0]))
        if len(hotels_already_added_query) == 0:
            acc_options = accommodation.get_accommodation_options(
                dest[1], check_in_date, check_out_date, {"adults": 2}, "hotel", 3, [], "GBP")
            for acc in acc_options:
                exists = db_manager.query("""
                SELECT id FROM hotel WHERE id = "{hotel_id}"
                """.format(hotel_id=acc["hotelId"]))
                if len(exists) == 0:
                    google_id = google_places.get_hotel_id(
                        acc["name"], acc["latitude"], acc["longitude"])
                    if google_id != None:
                        db_manager.insert("""
                        INSERT INTO hotel (id, provider, destination_id, google_id, name)
                        VALUES ("{hotel_id}", "amadeus", {
                                destination_id}, "{google_id}", "{hotel_name}")
                        """.format(hotel_id=acc["hotelId"], destination_id=dest[0], google_id=google_id, hotel_name=acc["name"]))


def populate_flyable_dests():
    origin = "LON"
    origin_id = db_manager.query("""
    SELECT id FROM destination WHERE city_code = "{origin}"
    ORDER BY population DESC LIMIT 1
    """.format(origin=origin))[0][0]
    durations = ["1,5"]
    for duration in durations:
        original_departure_date = datetime.strptime("2020-11-20", "%Y-%m-%d")

        for i in range(0, 1):
            departure_date = (original_departure_date + timedelta(days=i)
                              ).strftime("%Y-%m-%d")
            all_flights = amadeus.get_all_return_flights(
                origin, departure_date, duration)
            parsed_flights = flights.parse_flights(all_flights)
            for flight in parsed_flights:
                db_manager.insert("""
                REPLACE INTO flyable_destination (origin, destination, departure_date, return_date, name, price_amount, price_currency)
                VALUES ({origin_id}, {destination}, "{departure_date}",
                        "{return_date}", "{name}", {price_amount}, "{price_currency}")
                """.format(origin_id=origin_id, destination=flight["dest_id"], departure_date=flight["departureDate"], return_date=flight["returnDate"], name=flight["name"], price_amount=flight["price"]["amount"], price_currency=flight["price"]["currency"]))


def populate_dest_wiki():
    dests_query = db_manager.query("""
    SELECT destination.id, destination.name, country.Country FROM destination
    JOIN country ON country.ISO = destination.country_code
    WHERE wiki_description IS NULL AND tourist_score IS NOT NULL
    """)
    for dest_id, dest_name, country_name in dests_query:
        wiki_desc = wikipedia.get_wiki_description(
            dest_name + ", " + country_name)
        db_manager.insert("""
        UPDATE destination SET wiki_description = "{wiki_desc}"
        WHERE id = {dest_id}
        """.format(wiki_desc=wiki_desc, dest_id=dest_id))


def populate_weather_stations():
    n = 2958
    for i in range(1, n+1):
        weather_data = wmo.fetch_weather_data(i)
        if weather_data != None:
            db_manager.insert("""
            INSERT INTO weather_station (id, latitude, longitude, city_name)
            VALUES ({station_id}, {latitude}, {longitude}, "{city_name}")
            """.format(station_id=i, latitude=weather_data["cityLatitude"], longitude=weather_data["cityLongitude"], city_name=weather_data["cityName"]))


def populate_weather_data():
    n = 2958
    for i in range(703, n+1):
        weather_data = wmo.fetch_weather_data(i)
        if weather_data != None:
            climate_months = weather_data["climate"]["climateMonth"]
            for month in climate_months:
                db_manager.insert("""
                INSERT INTO climate (wmo_id, month, average_temp_c, num_days_rainfall)
                VALUES ({wmo_id}, {month}, {average_temp}, {num_days_rainfall})
                """.format(wmo_id=i, month=month["month"], average_temp=(float(month["maxTemp"])+float(month["minTemp"]))/2 if (month["maxTemp"] != None and month["minTemp"] != None and month["maxTemp"] != "" and month["minTemp"] != "") else "NULL", num_days_rainfall=month["raindays"] if (month["raindays"] != None and month["raindays"] != "") else "NULL"))


def populate_weather_ids():
    dests_query = db_manager.query("""
    SELECT id, latitude, longitude FROM destination
    WHERE tourist_score IS NOT NULL AND weather_station_id IS NULL
    ORDER BY tourist_score DESC
    """)
    for dest in dests_query:
        candidates_query = db_manager.query("""
        SELECT id, latitude, longitude FROM weather_station
        """)
        best_candidate = candidates_query[0]
        closest_distance = 1000000
        for candidate in candidates_query:
            d = distance.distance(
                (dest[1], dest[2]), (candidate[1], candidate[2])).km
            if d < closest_distance:
                closest_distance = d
                best_candidate = candidate
        db_manager.insert("""
        UPDATE destination SET weather_station_id = {station_id}
        WHERE id = {dest_id}
        """.format(dest_id=dest[0], station_id=best_candidate[0]))


# def populate_facebook_POI_details():
#     pois = db_manager.query("""
#     SELECT id, name, latitude, longitude FROM poi WHERE facebook_checkins IS NULL
#     """)
#     for poi in pois:
#         fb = facebook_places.search_facebook_place(poi[1], poi[2], poi[3])
#         if fb != None:
#             facebook_insert = db_manager.insert("""
#             UPDATE poi SET facebook_checkins = {checkins}, facebook_about = "{about}", facebook_description = "{description}"
#             WHERE id = "{poi_id}"
#             """.format(poi_id=poi[0], checkins=fb["checkins"], about=fb["about"].replace('"', '') if "about" in fb else "", description=fb["description"].replace('"', '') if "description" in fb else ""))


def populate_foursquare_POI_details():
    pois = db_manager.query("""
    SELECT poi.id, poi.name, poi.original_name, poi.latitude, poi.longitude, destination.name, destination.country_code
    FROM poi
    JOIN destination ON poi.destination_id = destination.id
    WHERE tourist_score IS NOT NULL AND foursquare_category_id IS NULL
    """)
    # WHERE foursquare_category_id IS NULL AND tourist_score IS NOT NULL
    forbidden_categories = [
        "4bf58dd8d48988d1e1931735", "4bf58dd8d48988d1ff931735"]
    for poi in pois:
        matches = foursquare.get_POI_match(
            poi[2] or poi[1], poi[3], poi[4], poi[5] + "," + poi[6])
        if matches != None and len(matches) > 0:
            i = 0
            found = False
            for match in matches:
                details = match
                if details["categories"][0]["id"] != None and details["categories"][0]["id"] not in forbidden_categories:
                    found = True
                    break
            if found == True:
                # details = details["venue"]
                foursquare_insert = db_manager.insert("""
                UPDATE poi SET foursquare_category_id = "{category_id}", cat_name = "{cat_name}"
                WHERE id = "{poi_id}"
                """.format(poi_id=poi[0], category_id=details["categories"][0]["id"] if len(details["categories"]) != 0 else "default", cat_name=details["categories"][0]["name"] if len(details["categories"]) != 0 else ""))


def populate_POI_table_from_google_details():
    pois = db_manager.query("""
    SELECT id FROM poi WHERE destination_id = 1796236
    """)
    for poi in pois:
        poi_details = google_places.get_poi_details(poi[0])
        db_manager.insert("""
        UPDATE poi SET name = "{name}", latitude = {latitude}, longitude = {longitude}, rating = {rating}, num_ratings = {num_ratings}, types = "{types}"
        WHERE id = {id}
        """.format(id=poi[0], name=poi_details["name"], latitude=poi_details["geometry"]["location"]["lat"], longitude=poi_details["geometry"]["location"]["lng"], rating=poi_details["rating"] if "rating" in poi else "NULL", num_ratings=poi_details["user_ratings_total"], types=str(poi_details["types"]).replace('"', '').replace("'", "")))
        for photo in poi_details["photos"]:
            db_manager.insert("""
            INSERT INTO poi_photo (reference, poi_id)
            VALUES ({reference}, {poi_id})
            """.format(reference=photo["reference"], poi_id=poi[0]))


def fetch_dest_image_urls():
    refs = db_manager.query("""
    SELECT reference FROM destination_photo WHERE url IS NULL
    """)
    for ref in refs:
        url = google_places.fetch_image_url(ref[0])
        db_manager.insert("""
        UPDATE destination_photo SET url = "{url}"
        WHERE reference = "{reference}"
        """.format(url=url, reference=ref[0]))


def fetch_POI_image_urls():
    refs = db_manager.query("""
    SELECT reference FROM poi_photo WHERE url IS NULL
    """)
    for ref in refs:
        url = google_places.fetch_image_url(ref[0])
        db_manager.insert("""
        UPDATE poi_photo SET url = "{url}"
        WHERE reference = "{reference}"
        """.format(url=url, reference=ref[0]))


def populate_POI_wiki_desc():
    pois = db_manager.query("""
    SELECT poi.id, poi.name, destination.name, destination.country_code FROM poi
    JOIN destination ON destination.id = poi.destination_id
    WHERE poi.num_ratings > 1000
    AND poi.destination_id=524901
    """)
    for poi in pois:
        search_term = poi[1]
        if poi[2] not in search_term:
            search_term += " " + poi[2]
        desc = wikipedia.get_wiki_description(search_term, sentences=4)
        db_manager.insert("""
        UPDATE poi SET wiki_description = "{desc}"
        WHERE id = "{id}"
        """.format(desc=desc, id=poi[0]))


def calculate_tourist_scores():
    dests = db_manager.query("""
    SELECT id FROM destination
    WHERE tourist_score IS NOT NULL AND city_code IS NOT NULL
    ORDER BY population DESC
    """)
    cat_totals = []
    for dest in dests:
        pois = db_manager.query("""
        SELECT rating, num_ratings, types, foursquare_category_id FROM poi
        WHERE destination_id = {dest_id}
        ORDER BY num_ratings DESC
        LIMIT 100
        """.format(dest_id=dest[0]))
        score = 0
        for poi in pois[:10]:
            if poi[0] != None and poi[1] != None:
                score += poi[0] * poi[1]
        db_manager.insert("""
        UPDATE destination SET tourist_score = {score}
        WHERE id = {dest_id}
        """.format(score=score, dest_id=dest[0]))
        cats = {"dest": dest[0], "culture": 1, "shopping": 1, "nightlife": 1}
        for poi in pois:
            types = poi[2]
            foursquare_cat = poi[3]
            if foursquare_cat == "4bf58dd8d48988d12d941735" or foursquare_cat == "4deefb944765f83613cdba6e":
                cats["culture"] += 1
            if "museum" in types:
                cats["culture"] += 1
            if "art_gallery" in types:
                cats["culture"] += 1
            if "place_of_worship" in types:
                cats["culture"] += 1
            if "nightclub" in types:
                cats["nightlife"] += 1
            if "bar" in types:
                cats["nightlife"] += 1
            if "casino" in types:
                cats["nightlife"] += 1
            if "shopping_mall" in types:
                cats["shopping"] += 1
            if "store" in types:
                cats["shopping"] += 1
            if "clothing_store" in types:
                cats["shopping"] += 1
            if "department_store" in types:
                cats["shopping"] += 1
        cat_totals.append(cats)
    max_culture = 1
    max_shopping = 1
    max_nightlife = 1
    for c in cat_totals:
        if c["culture"] > max_culture:
            max_culture = c["culture"]
        if c["shopping"] > max_shopping:
            max_shopping = c["shopping"]
        if c["nightlife"] > max_nightlife:
            max_nightlife = c["nightlife"]
    for c in cat_totals:
        db_manager.insert("""
        UPDATE destination
        SET culture_score = {culture_score}, shopping_score = {shopping_score}, nightlife_score = {nightlife_score}
        WHERE id = {dest_id}
        """.format(dest_id=c["dest"], culture_score=(c["culture"]/max_culture) * 10, shopping_score=(c["shopping"]/max_shopping) * 10, nightlife_score=(c["nightlife"]/max_nightlife) * 10))


def add_original_names():
    dests = db_manager.query("""
    SELECT destination.id, destination.latitude, destination.longitude, country.Languages
    FROM destination
    JOIN country ON country.ISO = destination.country_code
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL AND google_id IS NULL
    """)
    for dest in dests:
        lang = dest[3].split(',')[0].split('-')[0]
        pois = google_places.get_nearby_POIs(dest[1], dest[2], lang)
        for poi in pois:
            db_manager.insert("""
            UPDATE poi SET original_name = "{name}"
            WHERE id = "{poi_id}"
            """.format(name=poi["name"], poi_id=poi["place_id"]))


def add_missing_POIs_from_external_itineraries():
    dest_id = 2158177
    poi_names = ["Melbourne Central"]
    dest_query = db_manager.query("""
    SELECT latitude, longitude FROM destination
    WHERE id = {dest_id}
    """.format(dest_id=dest_id))
    for poi_name in poi_names:
        poi = google_places.search_for_POI(
            poi_name, dest_query[0][0], dest_query[0][1])
        db_manager.insert("""
        INSERT INTO poi (id, destination_id, name, latitude, longitude, rating, num_ratings, types)
        VALUES ("{id}", {destination_id}, "{name}", {latitude},
                {longitude}, {rating}, {num_ratings}, "{types}")
        """.format(id=poi["place_id"], destination_id=dest_id, name=poi["name"].replace('"', ''), latitude=poi["geometry"]["location"]["lat"], longitude=poi["geometry"]["location"]["lng"], rating=poi["rating"] if "rating" in poi else "NULL", num_ratings=poi["user_ratings_total"] if "user_ratings_total" in poi else "NULL", types=str(poi["types"]).replace('"', '').replace("'", "")))
        if "photos" in poi:
            for photo in poi["photos"]:
                db_manager.insert("""
                INSERT INTO poi_photo (reference, poi_id, height, width)
                VALUES ("{reference}", "{poi_id}", {height}, {width})
                """.format(reference=photo["photo_reference"], poi_id=poi["place_id"], height=photo["height"], width=photo["width"]))


def populate_POI_table():
    dests = db_manager.query("""
    SELECT id, latitude, longitude, name, country_code FROM destination
    WHERE city_code IS NOT NULL AND tourist_score IS NULL AND name = "London"
    ORDER BY population DESC
    LIMIT 1
    """)
    poisForDB = []
    for dest in dests:
        zones = get_city_zones(dest[0])
        for zone in zones:
            pois = google_places.get_nearby_POIs(
                zone["latitude"], zone["longitude"], zone["radius"], "en")
            for poi in pois:
                if poi_in_boundaries(dest[0], poi["geometry"]["location"]["lat"], poi["geometry"]["location"]["lng"]):
                    db_manager.insert("""
                    REPLACE INTO poi (id, destination_id, name, latitude, longitude, rating, num_ratings, types)
                    VALUES ("{id}", {destination_id}, "{name}", {latitude},
                            {longitude}, {rating}, {num_ratings}, "{types}")
                    """.format(id=poi["place_id"], destination_id=dest[0], name=poi["name"].replace('"', ''), latitude=poi["geometry"]["location"]["lat"], longitude=poi["geometry"]["location"]["lng"], rating=poi["rating"] if "rating" in poi else "NULL", num_ratings=poi["user_ratings_total"] if "user_ratings_total" in poi else "NULL", types=str(poi["types"]).replace('"', '').replace("'", "")))
                    if "photos" in poi:
                        for photo in poi["photos"]:
                            db_manager.insert("""
                            REPLACE INTO poi_photo (reference, poi_id, height, width)
                            VALUES ("{reference}", "{poi_id}",
                                    {height}, {width})
                            """.format(reference=photo["photo_reference"], poi_id=poi["place_id"], height=photo["height"], width=photo["width"]))
        db_manager.insert("""
        UPDATE destination SET tourist_score = 0
        WHERE id = {dest_id}
        """.format(dest_id=dest[0]))


def add_codes():
    codes_query = db_manager.query("""
    SELECT geonameid, name FROM destination_name WHERE isolanguage = "iata"
    """)
    for code in codes_query:
        ins = db_manager.insert("""
        UPDATE destination SET city_code = "{city_code}" WHERE id = {geoname_id}
        """.format(city_code=code[1], geoname_id=code[0]))


def populate_destination_images():

    dests_query = db_manager.query("""
    SELECT id, name, latitude, longitude FROM destination
    WHERE city_code IS NOT NULL AND tourist_score IS NOT NULL AND google_id IS NULL
    ORDER BY tourist_score DESC
    """)

    for dest in dests_query:
        google_id = google_places.fetch_dest_id(dest)
        db_manager.insert("""
        UPDATE destination SET google_id = "{google_id}"
        WHERE id = {dest_id}
        """.format(google_id=google_id, dest_id=dest[0]))

    dests_query = db_manager.query("""
    SELECT destination.id, destination.google_id FROM destination
    LEFT JOIN destination_photo ON destination.id=destination_photo.dest_id
    WHERE destination_photo.reference IS NULL AND tourist_score IS NOT NULL
    """)

    for dest in dests_query:
        exists = db_manager.query("""
        SELECT reference FROM destination_photo
        WHERE dest_id = {dest_id}
        """.format(dest_id=dest[0]))
        if len(exists) == 0:
            photos = google_places.fetch_images(dest[1])
            for photo in photos:
                db_manager.insert("""
                REPLACE INTO destination_photo (reference, dest_id, height, width)
                VALUES ("{ref}", "{dest_id}", {height}, {width})
                """.format(ref=photo["photo_reference"], dest_id=dest[0], height=photo["width"], width=photo["height"]))

    # for dest_id, dest_url in urls:
    #     # image_insert = db_manager.insert("""
    #     # UPDATE destination SET image_url = "{image_url}" WHERE id = {dest_id}
    #     # """.format(image_url=dest_url, dest_id=dest_id))
    #     # os.mkdir("assets/images/destinations/" + str(dest_id))
    #     user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
    #     headers = {'User-Agent': user_agent}
    #     req = urllib.request.Request(dest_url, {}, headers)
    #     with urllib.request.urlopen(req) as response, open("assets/images/destinations/" + str(dest_id) + "/1.jpg", 'wb') as out_file:
    #         data = response.read()
    #         out_file.write(data)


def get_missing_dest_images(dests):
    missing = []
    for dest_id, dest_name in dests:
        if not os.path.isdir("assets/images/destinations/" + str(dest_id)):
            missing.append((dest_id, dest_name))
    return missing


def calculate_destination_scores():
    poi_counts = db_manager.query("""
    SELECT destination_id, category_id, COUNT(id) FROM poi
    GROUP BY category_id, destination_id;
    """)
    scores = {}
    score_totals = {}
    for poi_count in poi_counts:
        if poi_count[0] in scores.keys():
            scores[poi_count[0]].append((poi_count[1], poi_count[2]))
        else:
            scores.update({poi_count[0]: [(poi_count[1], poi_count[2])]})

        if poi_count[0] in score_totals.keys():
            score_totals[poi_count[0]] += poi_count[2]
        else:
            score_totals.update({poi_count[0]: poi_count[2]})

    for dest_id, dest_scores in scores.items():
        feature_scores = {"culture": 0, "active": 0,
                          "nature": 0, "shopping": 0, "food": 0, "nightlife": 0}
        for dest_cat_score in dest_scores:
            poi_scores = db_manager.query("""
            SELECT culture_score, active_score, nature_score, shopping_score, food_score, nightlife_score FROM categories WHERE id = "{cat_id}";
            """.format(cat_id=dest_cat_score[0]))[0]
            feature_scores["culture"] += dest_cat_score[1] * poi_scores[0]
            feature_scores["active"] += dest_cat_score[1] * poi_scores[1]
            feature_scores["nature"] += dest_cat_score[1] * poi_scores[2]
            feature_scores["shopping"] += dest_cat_score[1] * poi_scores[3]
            feature_scores["food"] += dest_cat_score[1] * poi_scores[4]
            feature_scores["nightlife"] += dest_cat_score[1] * poi_scores[5]
        for feature, score in feature_scores.items():
            feature_scores[feature] = get_simplified_score(
                score, score_totals[dest_id])
        poi_counts = db_manager.insert("""
        UPDATE destination SET culture_score={culture_score}, active_score={active_score}, nature_score={nature_score}, shopping_score={shopping_score}, food_score={food_score}, nightlife_score={nightlife_score} WHERE id={dest_id};
        """ .format(culture_score=feature_scores["culture"], active_score=feature_scores["active"], nature_score=feature_scores["nature"], shopping_score=feature_scores["shopping"], food_score=feature_scores["food"], nightlife_score=feature_scores["nightlife"], dest_id=dest_id))


def get_simplified_score(score, total):
    normalised_score = score / total
    if normalised_score == 0:
        return 0
    elif normalised_score > 1:
        return 5
    else:
        return round(normalised_score / 0.2)
