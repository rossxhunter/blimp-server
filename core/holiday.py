from config import db_manager
from core.itinerary import calculate_itinerary
from flask import jsonify
from apis import amadeus
from core.destination import calculate_destination
from core import accommodation, flights
from util.util import get_origin_code
from util.db_populate import populate_DB


def get_holiday(constraints, softPrefs, prefScores):
    populate_DB()
    destination = calculate_destination(constraints, softPrefs, prefScores)

    dest_code_query = db_manager.query("""
    SELECT city_code FROM destination WHERE id={dest_id}
    """.format(dest_id=destination["id"]))

    city_id = dest_code_query[0][0]

    dest_id_for_travel = city_id

    if "destination" in constraints:
        if constraints["destination"]["type"] == "airport":
            dest_id_for_travel = constraints["destination"]["id"]

    origin_code = get_origin_code(constraints["origin"])

    accommodation_options = destination["accommodation"]

    travel_options = destination["flights"]

    travel, accommodation = choose_travel_and_accommodation(
        travel_options, accommodation_options, constraints["budget_leq"])

    itinerary = calculate_itinerary(
        destination["id"], travel, accommodation, constraints, softPrefs, prefScores)
    return jsonify(name=destination["name"], wiki=destination["wiki"], destId=destination["id"], itinerary=itinerary, travel=travel, accommodation=accommodation)


def choose_travel_and_accommodation(travel_options, accommodation_options, budget):
    best_score = 0
    for t in travel_options:
        print(t["price"])
    for acc in accommodation_options:
        score = acc["stars"]
        if score > best_score:
            if travel_options[0]["price"]["amount"] + acc["price"]["amount"] <= budget:
                best_score = score
                best_combo = (travel_options[0], acc)
    return best_combo
