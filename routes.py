from config import application, root_folder
from flask import request, session
from core import destination, holiday, itinerary
import json
from util import suggestions, evaluation, util
from flask.json import jsonify
from util.exceptions import NoResults
import uuid
from clicks import add_click
from config import db_manager
from core.itinerary import get_POIs_for_destination
from core.holiday import get_pois_list
import csv
from apis.exchange_rates import get_exchange_rate
from apis.s3 import upload_profile_picture
from apis.stripe import get_payment_cards, add_new_stripe_customer, add_new_card_for_customer, delete_card_for_customer
from apis import musement
from datetime import datetime
from util.user import generate_referral_code
from PIL import Image
import io
import boto
import os
from geopy import distance
from util import products


@application.route('/')
def root():
    return "You've reached the root of the API! Nothing interesing here..."


@application.route('/holiday', methods=['GET'])
def get_holiday():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    should_register_clicks = json.loads(
        request.args.get('should_register_clicks'))
    clicks_id = uuid.uuid4()

    return json.dumps(dict(clicks_id=clicks_id.hex, holiday=holiday.get_holiday(constraints, soft_prefs, pref_scores)))


@application.route('/city_details/<city>', methods=['GET'])
def get_city_details(city, origin=None, currency=None):
    currency = request.args.get('currency') or currency
    origin = request.args.get('origin') or origin
    city = int(city)
    city_query = db_manager.query("""
    SELECT name, wiki_description, destination.population, CurrencyName, Languages, country_code, MAX(average_temp_c), culture_score, shopping_score, nightlife_score, musement_id
    FROM destination
    JOIN country ON destination.country_code = country.ISO
    JOIN climate ON climate.weather_station_id = destination.weather_station_id
    WHERE id = {city}
    """.format(city=city))[0]
    musement_id = city_query[10]
    language_code = city_query[4].split(',')[0].split('-')[0]
    language_query = db_manager.query("""
    SELECT name FROM language
    WHERE iso = "{language_code}"
    """.format(language_code=language_code))[0]
    images_query = db_manager.query("""
    SELECT url FROM destination_photo
    WHERE dest_id = {city}
    """.format(city=city))
    images = []
    for image in images_query:
        images.append(image[0])
    attractions = products.get_attractions(city)
    tours = []
    if musement_id != None:
        raw_tours = musement.get_activities(musement_id, currency)
        for tour in raw_tours:
            if "duration_range" not in tour:
                duration = "n/a"
            else:
                duration = tour["duration_range"]["max"]
            if "latitude" not in tour:
                location = None
            else:
                location = {
                    "latitude": tour["latitude"], "longitude": tour["longitude"]}
            tours.append(
                {"id": tour["uuid"], "name": tour["title"], "location": location, "duration": duration, "price": tour["retail_price"]["value"], "category": tour["categories"][0]["name"],  "images": [tour["cover_image_url"].split("?w=")[0]], "rating": float(tour["reviews_avg"]), "description": tour["description"] if "description" in tour else "", "about": tour["about"]})

    similar_destinations = suggestions.fetch_similar_destinations(city)
    valid_dates = products.get_valid_dates(origin, city, currency)
    return jsonify({"id": city, "name": city_query[0], "validDates": valid_dates, "attractions": attractions, "tours": tours, "similarDestinations": similar_destinations, "images": images, "country_code": city_query[5], "description": city_query[1], "population": city_query[2], "currency": city_query[3], "language": language_query[0], "temperature": city_query[6], "culture": city_query[7], "shopping": city_query[8], "nightlife": city_query[9]})


@application.route('/holiday_from_feedback', methods=['GET'])
def get_holiday_from_feedback():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    feedback = json.loads(request.args.get('feedback'))

    return holiday.get_holiday(constraints, soft_prefs, pref_scores, feedback)


@application.route('/itinerary_from_change', methods=['GET'])
def get_itinerary_from_change():
    destination_id = json.loads(request.args.get('destination_id'))
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    travel = json.loads(request.args.get('travel'))
    accommodation = json.loads(request.args.get('accommodation'))

    pois, max_popularity = get_POIs_for_destination(
        destination_id, pref_scores, False)

    return jsonify(itinerary.calculate_itinerary(
        dict(pois), travel, accommodation, constraints, soft_prefs, pref_scores, max_popularity))


@application.route('/itinerary', methods=['GET'])
def get_itinerary():
    activities = json.loads(request.args.get('activities'))
    window = json.loads(request.args.get('window'))
    day = int(request.args.get('day'))
    travel = json.loads(request.args.get('travel'))
    accommodation = json.loads(request.args.get('accommodation'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    dest_id = json.loads(request.args.get('destId'))
    pois, max_popularity = get_POIs_for_destination(
        dest_id, pref_scores, False)
    essential_travel_methods = []
    pois = {}
    poi_order = [{"id": a["id"], "duration": a["duration"] if "duration" in a else a["averageDuration"]}
                 for a in activities]
    for activity in activities:
        if activity["id"] in pois:
            raise NoResults("Already added this activity")
        pois[activity["id"]] = activity
        if "travelMethodChanged" in activity and activity["travelMethodChanged"] == True:
            essential_travel_methods.append({
                "id": activity["id"], "method": activity["travelMethodToNext"]})
    return jsonify(itinerary.calculate_itinerary(pois, travel, accommodation, constraints, soft_prefs, pref_scores, max_popularity, poi_order=poi_order, day=day, window=window, essential_travel_methods=essential_travel_methods)[0])


@application.route('/itinerary_for_evaluation/<dest_id>', methods=['GET'])
def get_itinerary_for_evaluation(dest_id):
    activities = json.loads(request.args.get('activities'))
    day = json.loads(request.args.get('day'))
    window = json.loads(request.args.get('window'))
    pois = {}
    essential_travel_methods = []
    poi_order = [{"id": a["id"], "duration": a["duration"] if "duration" in a else a["averageDuration"]}
                 for a in activities]
    for activity in activities:
        if activity["id"] in pois:
            raise NoResults("Already added this activity")
        pois[activity["id"]] = activity
        if "travelMethodChanged" in activity and activity["travelMethodChanged"] == True:
            essential_travel_methods.append({
                "id": activity["id"], "method": activity["travelMethodToNext"]})
    return jsonify(itinerary.calculate_itinerary_for_evaluation(
        dest_id, 3, poi_order, day, window, essential_travel_methods)[0])


@application.route('/itineraries_for_evaluation/<dest_id>', methods=['GET'])
def get_itineraries_for_evaluation(dest_id):
    pois, max_popularity = get_POIs_for_destination(dest_id, {}, False)
    pois_list = get_pois_list(pois)
    google_itinerary = evaluation.get_external_itinerary("google", dest_id)
    inspirock_itinerary = evaluation.get_external_itinerary(
        "inspirock", dest_id)
    grid = [1, 10, 100, 1000]
    with open('evaluation_hyper_values.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        hyperparams = {"popularity": 100, "rating": 30,
                       "travel_time": 2, "diversity": 20}
        fixed_hyperparams = dict(hyperparams)
        blimp_itinerary_hyper = itinerary.calculate_itinerary_for_evaluation(
            dest_id, 3, hyperparams=hyperparams)
        blimp_evaluation_values = get_evaluation_values(
            blimp_itinerary_hyper, max_popularity)
        if blimp_evaluation_values != None:
            writer.writerow([fixed_hyperparams, blimp_evaluation_values["popularity"], blimp_evaluation_values["rating"],
                             blimp_evaluation_values["travel_time"], blimp_evaluation_values["diversity"]])

    blimp_itinerary = itinerary.calculate_itinerary_for_evaluation(dest_id, 3)
    google_itinerary_with_details = evaluation.get_poi_details_for_itinerary(
        google_itinerary)
    inspirock_itinerary_with_details = evaluation.get_poi_details_for_itinerary(
        inspirock_itinerary)

    clicks_id = uuid.uuid4()
    blimp_evaluation_values = get_evaluation_values(
        blimp_itinerary, max_popularity)
    google_evaluation_values = get_evaluation_values(
        google_itinerary_with_details, max_popularity)
    inspirock_evaluation_values = get_evaluation_values(
        inspirock_itinerary_with_details, max_popularity)
    with open('evaluation_values.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(
            [dest_id, blimp_evaluation_values["popularity"], google_evaluation_values["popularity"], inspirock_evaluation_values["popularity"], dest_id, blimp_evaluation_values["rating"], google_evaluation_values["rating"], inspirock_evaluation_values["rating"], dest_id, blimp_evaluation_values["travel_time"], google_evaluation_values["travel_time"], inspirock_evaluation_values["travel_time"], dest_id, blimp_evaluation_values["diversity"], google_evaluation_values["diversity"], inspirock_evaluation_values["diversity"]])
    return jsonify(itineraries=dict(blimp=blimp_itinerary, google=google_itinerary_with_details, inspirock=inspirock_itinerary_with_details), all_activities=pois_list, clicks_id=clicks_id.hex)


def get_evaluation_values(itinerary, max_popularity):
    total_popularity = 0
    total_rating = 0
    total_travel_time = 0
    categories_count = {}
    count = 0
    for day in itinerary.items():
        day = day[1]
        for poi in day:
            total_popularity += poi["popularity"] / max_popularity
            total_rating += poi["rating"]
            total_travel_time += poi["travelTimeToNext"] or 0
            if poi["category"] in categories_count:
                categories_count[poi["category"]] += 1
            else:
                categories_count[poi["category"]] = 1
            count += 1
    if count > 1:
        diversity_index = util.calculate_diversity_index(
            categories_count, count)
        return {"popularity": total_popularity/count, "rating": total_rating/count, "travel_time": total_travel_time/count, "diversity": diversity_index}
    else:
        return None


@application.route('/suggestions', methods=['GET'])
def get_all_suggestions():
    return jsonify(suggestions.fetch_all_suggestions())


@application.route('/suggestions/<suggestion>', methods=['GET'])
def get_suggestions(suggestion):
    return jsonify(suggestions.fetch_suggestions(suggestion))


@application.route('/clicks/<clicks_id>/<click_name>', methods=['POST'])
def post_click(clicks_id, click_name):
    mode = request.form['mode']
    metadata = request.form['metadata']
    add_click(clicks_id, click_name, mode, metadata)
    return "Success"


@application.route('/user', methods=['POST'])
def add_new_user():
    uid = request.form['id']
    email = request.form['email']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    referral_code = generate_referral_code()
    stripe_id = add_new_stripe_customer()
    db_manager.insert("""
    INSERT INTO user (id, email, first_name, last_name, referral_code, stripe_id)
    VALUES ("{uid}", "{email}", "{first_name}", "{last_name}", "{referral_code}", "{stripe_id}")
    """.format(uid=uid, email=email, first_name=first_name, last_name=last_name, referral_code=referral_code, stripe_id=stripe_id))
    return "Success"


@application.route('/user/<uid>', methods=['GET'])
def get_user_details(uid):
    user_details = fetch_user_details(uid)
    return jsonify(user_details)


def fetch_user_details(uid):
    user_details = db_manager.query("""
    SELECT id, email, first_name, last_name, currency, referral_code, bookings, searches, shares, score, profile_picture, stripe_id
    FROM user
    WHERE id = "{uid}"
    """.format(uid=uid))[0]
    cards = get_payment_cards(user_details[11])
    return {"id": user_details[0], "email": user_details[1], "firstName": user_details[2], "lastName": user_details[3], "currency": user_details[4], "referralCode": user_details[5], "bookings": user_details[6], "searches": user_details[7], "shares": user_details[8], "score": user_details[9], "profilePicture": user_details[10], "travellers": get_travellers_details(uid), "trips": get_user_trips(uid), "paymentCards": cards}


def get_user_trips(uid):
    trips_query = db_manager.query("""
    SELECT trip.id, type, destination, departure_date, return_date, destination.name, destination.country_code, destination_photo.url
    FROM trip
    JOIN destination ON destination.id = trip.destination
    JOIN destination_photo ON destination_photo.reference = (
        SELECT d.reference FROM destination_photo AS d
        WHERE d.dest_id = trip.destination
        LIMIT 1
    )
    WHERE user = "{uid}"
    """.format(uid=uid))
    saved_trips = []
    upcoming_trips = []
    past_trips = []
    for t in trips_query:
        trip = {"id": t[0], "destination": t[2], "departureDate": datetime.strftime(
            t[3], "%Y-%m-%d"), "returnDate": datetime.strftime(t[4], "%Y-%m-%d"), "name": t[5], "countryCode": t[6], "photo": t[7]}
        if t[1] == "saved":
            saved_trips.append(trip)
        elif t[1] == "upcoming":
            upcoming_trips.append(trip)
        elif t[1] == "past":
            past_trips.append(trip)
    return {"saved": saved_trips, "upcoming": upcoming_trips, "past": past_trips}


def get_travellers_details(uid):
    travellers_query = db_manager.query("""
    SELECT id, full_name, dob, sex, street_address, city, region, postcode, country, passport_number
    FROM traveller
    WHERE user = "{uid}"
    """.format(uid=uid))
    travellers = []
    for t in travellers_query:
        travellers.append({"id": t[0], "fullName": t[1], "dob": None if t[2] == None else datetime.strftime(t[2], "%Y-%m-%d"), "sex": t[3], "streetAddress": t[4],
                           "city": t[5], "region": t[6], "postcode": t[7], "country": t[8], "passportNumber": t[9]})
    return travellers


def add_speech_marks_or_nullify(s):
    if s == None:
        return "NULL"
    else:
        return '"' + s + '"'


@application.route('/user/<uid>/traveller/<traveller_id>', methods=['PUT'])
def update_traveller(uid, traveller_id):
    values = request.form
    old_values_query = db_manager.query("""
    SELECT full_name, dob, sex, street_address, city, region, postcode, country, passport_number
    FROM traveller
    WHERE id = "{traveller_id}"
    """.format(traveller_id=traveller_id))[0]
    full_name = add_speech_marks_or_nullify(
        values["fullName"] if "fullName" in values else old_values_query[0])
    dob = add_speech_marks_or_nullify(
        values["dob"] if "dob" in values else (None if old_values_query[1] == None else datetime.strftime(old_values_query[1], "%Y-%m-%d")))
    sex = add_speech_marks_or_nullify(
        values["sex"] if "sex" in values else old_values_query[2])
    street_address = add_speech_marks_or_nullify(values[
        "streetAddress"] if "streetAddress" in values else old_values_query[3])
    city = add_speech_marks_or_nullify(
        values["city"] if "city" in values else old_values_query[4])
    region = add_speech_marks_or_nullify(
        values["region"] if "region" in values else old_values_query[5])
    postcode = add_speech_marks_or_nullify(
        values["postcode"] if "postcode" in values else old_values_query[6])
    country = add_speech_marks_or_nullify(
        values["country"] if "country" in values else old_values_query[7])
    passport_number = add_speech_marks_or_nullify(
        values["passportNumber"] if "passportNumber" in values else old_values_query[8])

    db_manager.insert("""
    UPDATE traveller
    SET full_name={full_name}, dob={dob}, sex={sex}, street_address = {street_address}, city = {city}, region = {region}, postcode = {postcode}, country = {country}, passport_number={passport_number}
    WHERE id = {traveller_id}
    """.format(full_name=full_name, dob=dob, sex=sex, street_address=street_address, city=city, region=region, postcode=postcode, country=country, passport_number=passport_number, traveller_id=traveller_id))
    return jsonify(get_travellers_details(uid))


@application.route('/user/<uid>/traveller', methods=['POST'])
def add_new_traveller(uid):
    db_manager.insert("""
    INSERT INTO traveller (user)
    VALUES ("{uid}")
    """.format(uid=uid))
    return jsonify(get_travellers_details(uid))


@application.route('/user/<uid>/traveller/<traveller_id>', methods=['DELETE'])
def delete_traveller(uid, traveller_id):
    db_manager.insert("""
    DELETE FROM traveller
    WHERE id = {traveller_id}
    """.format(traveller_id=traveller_id))
    return jsonify(get_travellers_details(uid))


@application.route('/holiday', methods=['POST'])
def post_holiday():
    type = request.form['type']
    uid = request.form['user']
    destination = request.form['destination']
    departure_date = request.form['departure_date']
    return_date = request.form['return_date']
    db_manager.insert("""
    REPLACE INTO trip (user, type, destination, departure_date, return_date)
    VALUES ("{uid}", "{type}", "{destination}", "{departure_date}", "{return_date}")
    """.format(uid=uid, type=type, destination=destination, departure_date=departure_date, return_date=return_date))
    return jsonify(get_user_trips(uid)[type])


@application.route('/holiday/<type>/<uid>/<holiday_id>', methods=['DELETE'])
def delete_holiday(type, uid, holiday_id):
    db_manager.insert("""
    DELETE FROM trip
    WHERE id = {trip_id}
    """.format(trip_id=holiday_id))
    return jsonify(get_user_trips(uid)[type])


@application.route('/user/searches/<uid>', methods=['PUT'])
def increment_searches(uid):
    db_manager.insert("""
    UPDATE user
    SET searches = searches + 1
    WHERE id = "{uid}"
    """.format(uid=uid))
    searches_query = db_manager.query("""
    SELECT searches
    FROM user
    WHERE id = "{uid}"
    """.format(uid=uid))
    return jsonify({"searches": searches_query[0][0], "score": calculate_blimp_score(uid)})


def calculate_blimp_score(uid):
    counts = db_manager.query("""
    SELECT bookings, searches, shares
    FROM user
    WHERE id = "{uid}"
    """.format(uid=uid))[0]
    score = blimp_score(counts[0], counts[1], counts[2])
    db_manager.insert("""
    UPDATE user
    SET score = {score}
    WHERE id = "{uid}"
    """.format(score=score, uid=uid))
    return score


def blimp_score(bookings, searches, shares):
    return 100 * bookings + 5 * searches + 10 * shares


@application.route('/user/<uid>', methods=['PUT'])
def update_user_details(uid):
    values = request.form
    old_values_query = db_manager.query("""
    SELECT first_name, last_name, email
    FROM user
    WHERE id = "{uid}"
    """.format(uid=uid))[0]
    firstName = values["firstName"] if "firstName" in values else old_values_query[0]
    lastName = values["lastName"] if "lastName" in values else old_values_query[1]
    email = values["email"] if "email" in values else old_values_query[2]
    db_manager.insert("""
    UPDATE user
    SET first_name = "{firstName}", last_name = "{lastName}", email = "{email}"
    WHERE id = "{uid}"
    """.format(uid=uid, firstName=firstName, lastName=lastName, email=email))
    return jsonify(fetch_user_details(uid))


@application.route('/activity/<activity_id>', methods=['GET'])
def get_activity_details(activity_id):
    currency = request.args.get('currency')
    tickets = []
    venue_id = db_manager.query("""
    SELECT musement_id
    FROM poi
    WHERE id = "{poi_id}"
    """.format(poi_id=activity_id))[0][0]
    if venue_id != None:
        raw_tickets = musement.get_activities_for_venue(venue_id, currency)
        tickets = []
        for ticket in raw_tickets:
            if "duration_range" not in ticket:
                duration = "n/a"
            else:
                duration = ticket["duration_range"]["max"]
            tickets.append(
                {"id": ticket["uuid"], "name": ticket["title"], "duration": duration, "price": ticket["retail_price"]["value"], "category": ticket["categories"][0]["name"],  "images": [ticket["cover_image_url"].split("?w=")[0]], "rating": float(ticket["reviews_avg"]), "description": ticket["description"] if "description" in ticket else "", "about": ticket["about"]})

    details = products.fetch_activity_details(activity_id)
    details["tickets"] = tickets
    return jsonify(details)


@application.route('/hotel/<hotel_id>', methods=['GET'])
def get_hotel_details(hotel_id):
    hotel = db_manager.query("""
    SELECT name, latitude, longitude, stars, street_address, postcode, amenities, description
    FROM hotel
    WHERE id = "{hotel_id}"
    """.format(hotel_id=hotel_id))
    hotel_images = db_manager.query("""
    SELECT url, type
    FROM hotel_photo
    WHERE hotel_id = "{hotel_id}"
    """.format(hotel_id=hotel_id))
    images = []
    for image in hotel_images:
        images.append({"url": image[0], "type": image[1]})
    hotel_ratings = db_manager.query("""
    SELECT overall, sleep_quality, service, facilities, room_comforts, value_for_money, catering, swimming_pool, location, internet, points_of_interest, staff
    FROM hotel_rating
    WHERE hotel = "{hotel_id}"
    """.format(hotel_id=hotel_id))
    if len(hotel_ratings) == 0:
        rating = None
    else:
        rating = {"overall": hotel_ratings[0][0], "sleep_quality": hotel_ratings[0][1], "service": hotel_ratings[0][2], "facilities": hotel_ratings[0][3], "room_comforts": hotel_ratings[0][4], "value_for_money": hotel_ratings[0]
                  [5], "catering": hotel_ratings[0][6], "swimming_pool": hotel_ratings[0][7], "location": hotel_ratings[0][8], "internet": hotel_ratings[0][9], "points_of_interest": hotel_ratings[0][10], "staff": hotel_ratings[0][11]}

    hotel_details = {"name": hotel[0][0], "latitude": hotel[0][1], "longitude": hotel[0][2],
                     "stars": hotel[0][3], "address": {"streetAddress": hotel[0][4], "postcode": hotel[0][5]}, "amenities": json.loads(hotel[0][6]), "description": hotel[0][7], "images": images, "rating": rating}
    return jsonify(hotel_details)


@application.route('/random_destination', methods=['GET'])
def get_random_destination():
    origin = request.args.get('origin')
    currency = request.args.get('currency')
    dest = db_manager.query("""
    SELECT id
    FROM destination
    WHERE tourist_score IS NOT NULL
    ORDER BY RAND()
    LIMIT 1
    """)
    return get_city_details(dest[0][0], origin=origin, currency=currency)


@application.route('/user/profile_picture/<user_id>', methods=['POST'])
def add_profile_picture(user_id):
    image = request.files.get("image")
    image_path = "{root_folder}/tmp/{user_id}.jpg".format(
        root_folder=root_folder, user_id=user_id)
    image.save(image_path)
    upload_profile_picture(user_id, image_path)
    os.remove(image_path)
    db_manager.insert("""
    UPDATE user
    SET profile_picture = "https://blimp-resources.s3.eu-west-2.amazonaws.com/profile_pictures/{user_id}.jpg"
    WHERE id = "{user_id}"
    """.format(user_id=user_id))
    return "Success"


@application.route('/user/<user_id>/payment_card', methods=['POST'])
def add_new_payment_card(user_id):
    customer_id = db_manager.query("""
    SELECT stripe_id
    FROM user
    WHERE id = "{user_id}"
    """.format(user_id=user_id))[0][0]
    card_number = request.form["card_number"]
    card_holder_name = request.form["card_holder_name"]
    expiry_date_month = int(request.form["expiry_date_month"])
    expiry_date_year = int("20" + request.form["expiry_date_year"])
    cvv_code = request.form["cvv_code"]

    new_card = add_new_card_for_customer(customer_id, card_number,
                                         expiry_date_month, expiry_date_year, cvv_code, card_holder_name)
    return jsonify(new_card)


@application.route('/user/<uid>/payment_card/<card_id>', methods=['DELETE'])
def delete_payment_card(uid, card_id):
    customer_id = db_manager.query("""
    SELECT stripe_id
    FROM user
    WHERE id = "{user_id}"
    """.format(user_id=uid))[0][0]
    delete_card_for_customer(customer_id, card_id)
    return "Success"


@application.route('/tour/<activity_id>', methods=['GET'])
def get_tour_details(activity_id):
    currency = request.args.get('currency')
    details = musement.get_activity(activity_id, currency)
    details["pois"] = []
    for venue in details["venues"]:
        poi_query = db_manager.query("""
        SELECT id
        FROM poi
        WHERE musement_id = {musement_id}
        LIMIT 1
        """.format(musement_id=venue["id"]))
        if len(poi_query) != 0:
            poi = products.fetch_activity_details(poi_query[0][0])
            details["pois"].append(poi)
    images = musement.get_images(activity_id)
    details["images"] = images
    return jsonify(details)
