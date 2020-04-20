from config import application
from flask import request
from core import destination, holiday, itinerary
import json
from util import suggestions
from flask.json import jsonify
from util.exceptions import NoResults


@application.route('/')
def root():
    return "You've reached the root of the API! Nothing interesing here..."


@application.route('/holiday', methods=['GET'])
def get_holiday():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    return holiday.get_holiday(constraints, soft_prefs, pref_scores)


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


@application.route('/suggestions', methods=['GET'])
def get_suggestions():
    suggestion = request.args.get('suggestion')
    return suggestions.fetch_suggestions(suggestion)
