from config import application
from flask import request
import core.destination as destination
import core.holiday as holiday
import json
import util.suggestions as suggestions


@application.route('/')
def root():
    return "You've reached the root of the API! Nothing interesing here..."


@application.route('/holiday', methods=['GET'])
def get_holiday():
    constraints = json.loads(request.args.get('constraints'))
    soft_prefs = json.loads(request.args.get('softprefs'))
    pref_scores = json.loads(request.args.get('pref_scores'))
    return holiday.get_holiday(constraints, soft_prefs, pref_scores)


@application.route('/suggestions', methods=['GET'])
def get_suggestions():
    suggestion = request.args.get('suggestion')
    return suggestions.fetch_suggestions(suggestion)
