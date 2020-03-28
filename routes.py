from config import application
from flask import request
import core.destination as destination
import core.itinerary as itinerary
import json
import util.suggestions as suggestions


@application.route('/')
def root():
    return "Home!"


@application.route('/itinerary', methods=['GET'])
def get_itinerary():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    destination = request.args.get('destination')
    return itinerary.calculate_itinerary(destination, constraints, soft_prefs, pref_scores)


@application.route('/destination', methods=['GET'])
def get_destination():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    return destination.calculate_destination(constraints, soft_prefs, pref_scores)


@application.route('/suggestions', methods=['GET'])
def get_suggestions():
    suggestion = request.args.get('suggestion')
    return suggestions.fetch_suggestions(suggestion)
