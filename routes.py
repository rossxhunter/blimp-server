from config import application
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
def get_city_details(city):
    currency = request.args.get('currency')
    origin = request.args.get('origin')
    city = int(city)
    city_query = db_manager.query("""
    SELECT name, wiki_description, destination.population, CurrencyName, Languages, country_code, MAX(average_temp_c), culture_score, shopping_score, nightlife_score FROM destination
    JOIN country ON destination.country_code = country.ISO
    JOIN climate ON climate.weather_station_id = destination.weather_station_id
    WHERE id = {city}
    """.format(city=city))
    language_code = city_query[0][4].split(',')[0].split('-')[0]
    language_query = db_manager.query("""
    SELECT name FROM language
    WHERE iso = "{language_code}"
    """.format(language_code=language_code))
    images_query = db_manager.query("""
    SELECT url FROM destination_photo
    WHERE dest_id = {city}
    """.format(city=city))
    images = []
    for image in images_query:
        images.append(image[0])
    attractions_query = db_manager.query("""
    SELECT poi.name, categories.name, categories.icon_prefix, poi_photo.url, poi.rating
    FROM poi
    JOIN poi_photo ON poi_photo.reference = (
        SELECT p.reference FROM poi_photo AS p
        WHERE p.poi_id = poi.id
        LIMIT 1
    )
    JOIN categories ON categories.id = foursquare_category_id
    WHERE poi.destination_id = {city}
    ORDER BY poi.num_ratings DESC
    """.format(city=city))
    attractions = []
    for i in range(0, min(len(attractions_query), 5)):
        attractions.append(
            {"name": attractions_query[i][0], "category": attractions_query[i][1], "categoryIcon": attractions_query[i][2], "bestPhoto": attractions_query[i][3], "rating": attractions_query[i][4], "description": ""})
    similar_destinations = suggestions.fetch_similar_destinations(city)
    valid_dates_query = db_manager.query("""
    SELECT departure_date, return_date, price_amount, price_currency
    FROM flyable_destination
    WHERE origin = {origin} AND destination = {destination}
    """.format(origin=origin, destination=city))
    valid_dates = []
    if len(valid_dates_query) > 0:
        conversion_rate = get_exchange_rate(valid_dates_query[0][3], currency)
        for vd in valid_dates_query:
            price = vd[2] * conversion_rate
            valid_dates.append(
                {"departureDate": vd[0].strftime("%Y-%m-%d"), "returnDate": vd[1].strftime("%Y-%m-%d"), "price": price})
    return jsonify({"id": city, "name": city_query[0][0], "validDates": valid_dates, "attractions": attractions, "similarDestinations": similar_destinations, "images": images, "country_code": city_query[0][5], "description": city_query[0][1], "population": city_query[0][2], "currency": city_query[0][3], "language": language_query[0][0], "temperature": city_query[0][6], "culture": city_query[0][7], "shopping": city_query[0][8], "nightlife": city_query[0][9]})


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


@application.route('/suggestions/<suggestion>', methods=['GET'])
def get_suggestions(suggestion):
    return suggestions.fetch_suggestions(suggestion)


@application.route('/clicks/<clicks_id>/<click_name>', methods=['POST'])
def post_click(clicks_id, click_name):
    mode = request.body['mode']
    metadata = request.body['metadata']
    add_click(clicks_id, click_name, mode, metadata)
    return "Success"


@application.route('/user', methods=['POST'])
def post_new_user():
    uid = request.body['id']
    email = request.body['email']
    first_name = request.body['first_name']
    last_name = request.body['last_name']
    db_manager.insert("""
    INSERT INTO user (id, email, first_name, last_name)
    VALUES ("{uid}", "{email}", "{first_name}", "{last_name}")
    """.format(uid=uid, email=email, first_name=first_name, last_name=last_name))
    return "Success"


@application.route('/user/<uid>', methods=['GET'])
def get_user_details(uid):
    user_details = db_manager.query("""
    SELECT id, email, first_name, last_name, currency, referral_code, bookings, searches, shares, score
    FROM user
    WHERE id = "{uid}"
    """.format(uid=uid))
    return jsonify({"id": user_details[0][0], "email": user_details[0][1], "firstName": user_details[0][2], "lastName": user_details[0][3], "currency": user_details[0][4], "referralCode": user_details[0][5], "bookings": user_details[0][6], "searches": user_details[0][7], "shares": user_details[0][8], "score": user_details[0][9], "travellers": get_travellers_details(uid), "trips": get_user_trips(uid)})


def get_user_trips(uid):
    trips_query = db_manager.query("""
    SELECT type, destination, departure_date, return_date
    FROM trip
    WHERE user = "{uid}"
    """.format(uid=uid))
    saved_trips = []
    upcoming_trips = []
    past_trips = []
    for t in trips_query:
        if t[0] == "saved":
            saved_trips.append(
                {"destination": t[1], "departureDate": t[2], "return_date": t[3]})
        elif t[0] == "upcoming":
            upcoming_trips.append(
                {"destination": t[1], "departureDate": t[2], "return_date": t[3]})
        elif t[0] == "past":
            past_trips.append(
                {"destination": t[1], "departureDate": t[2], "return_date": t[3]})
    return {"saved": saved_trips, "upcoming": upcoming_trips, "past": past_trips}


def get_travellers_details(uid):
    travellers_query = db_manager.query("""
    SELECT id, full_name, dob, sex, street_address, city, region, postcode, country, passport_number
    FROM traveller
    WHERE user = "{uid}"
    """.format(uid=uid))
    travellers = []
    for t in travellers_query:
        travellers.append({"id": t[0], "fullName": t[1], "dob": t[2], "sex": t[3], "streetAddress": t[4],
                           "city": t[5], "region": t[6], "postcode": t[7], "country": t[8], "passportNumber": t[9]})
    return travellers


@application.route('/user/<uid>/traveller/<traveller_id>/address', methods=['PUT'])
def update_traveller_address(uid, traveller_id):
    values = request.form
    db_manager.insert("""
    UPDATE traveller
    SET street_address = "{streetAddress}", city = "{city}", region = "{region}", postcode = "{postcode}", country = "{country}"
    WHERE id = {traveller_id}
    """.format(streetAddress=values["streetAddress"], city=values["city"], region=values["region"], postcode=values["postcode"], country=values["country"], traveller_id=traveller_id))
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
