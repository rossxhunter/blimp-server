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
    city = int(city)
    city_query = db_manager.query("""
    SELECT name, wiki_description, destination.population, CurrencyName, Languages, country_code, MAX(average_temp_c) FROM destination
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
    return jsonify({"id": city, "name": city_query[0][0], "attractions": attractions, "similarDestinations": similar_destinations, "images": images, "country_code": city_query[0][5], "description": city_query[0][1], "population": city_query[0][2], "currency": city_query[0][3], "language": language_query[0][0], "temperature": city_query[0][6]})


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

    return itinerary.calculate_itinerary(
        dict(pois), travel, accommodation, constraints, soft_prefs, pref_scores, max_popularity)


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
    mode = request.headers['mode']
    metadata = request.headers['metadata']
    add_click(clicks_id, click_name, mode, metadata)
    return "Success"
