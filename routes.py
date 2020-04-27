from config import application
from flask import request, session
from core import destination, holiday, itinerary
import json
from util import suggestions, evaluation
from flask.json import jsonify
from util.exceptions import NoResults
import uuid
from clicks import add_new_clicks_record, increment_click
from config import db_manager


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
    if (should_register_clicks):
        add_new_clicks_record(clicks_id.hex)

    return json.dumps(dict(clicks_id=clicks_id.hex, holiday=holiday.get_holiday(constraints, soft_prefs, pref_scores)))


@application.route('/holiday_from_feedback', methods=['GET'])
def get_holiday_from_feedback():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    feedback = json.loads(request.args.get('feedback'))

    return holiday.get_holiday(constraints, soft_prefs, pref_scores, feedback)


@application.route('/itinerary', methods=['GET'])
def get_itinerary():
    activities = json.loads(request.args.get('activities'))
    day = int(request.args.get('day'))
    travel = json.loads(request.args.get('travel'))
    accommodation = json.loads(request.args.get('accommodation'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))

    pois = {}
    poi_order = [a["id"] for a in activities]
    for activity in activities:
        if activity["id"] in pois:
            raise NoResults("Already added this activity")
        pois[activity["id"]] = activity
    return jsonify(itinerary.calculate_itinerary(pois, travel, accommodation, constraints, soft_prefs, pref_scores, poi_order, day)[0])


@application.route('/itineraries_for_evaluation/<dest_id>', methods=['GET'])
def get_itineraries_for_evaluation(dest_id):
    google_itinerary = evaluation.get_external_itinerary("google", dest_id)
    origin_id = 2643743
    preferences = {}
    constraints = dict(trip_type="Return", origin={"type": "city", "id": origin_id}, destination={"type": "city", "id": dest_id},
                       departure_date="2020-07-16", return_date="2020-07-18", travellers={"adults": 0}, accommodation_stars=3, budget_leq=1500)
    soft_prefs = []
    pref_scores = []
    blimp_itinerary = itinerary.calculate_itinerary_for_evaluation(dest_id, 3,
                                                                   constraints, soft_prefs, pref_scores)
    google_itinerary_with_details = evaluation.get_poi_details_for_itinerary(
        google_itinerary)
    return jsonify(blimp=blimp_itinerary, google=google_itinerary_with_details)


@application.route('/suggestions/<suggestion>', methods=['GET'])
def get_suggestions(suggestion):
    return suggestions.fetch_suggestions(suggestion)


@application.route('/clicks/<clicks_id>/<click_name>', methods=['POST'])
def post_click(clicks_id, click_name):
    increment_click(clicks_id, click_name)
    return "Success"
