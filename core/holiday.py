from config import db_manager
from core.itinerary import calculate_itinerary
from flask import jsonify
from apis import amadeus
from core.destination import calculate_destination
from core import accommodation, flights
from util.util import get_origin_code


def get_holiday(constraints, softPrefs, prefScores):

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

    # travel_options = get_travel_options(
    #     origin_code, dest_id_for_travel, constraints["departure_date"], constraints["return_date"], constraints["travellers"], constraints["budget_currency"])
    # accommodation_options = get_accommodation_options(
    #     city_id, constraints["departure_date"], constraints["return_date"], constraints["travellers"], constraints["accommodation_type"], constraints["accommodation_stars"], constraints["accommodation_amenities"], constraints["budget_currency"])

    accommodation_options = destination["accommodation"]

    travel_options = destination["flights"]

    travel, accommodation = choose_travel_and_accommodation(
        travel_options, accommodation_options)

    itinerary = calculate_itinerary(
        destination["id"], accommodation, constraints, softPrefs, prefScores)
    return jsonify(name=destination["name"], wiki=destination["wiki"], destId=destination["id"], itinerary=itinerary, travel=travel, accommodation=accommodation)


def choose_travel_and_accommodation(travel_options, accommodation_options):
    return travel_options[0], accommodation_options[2]


def get_travel_options(origin, dest, departure_date, return_date, travellers, currency):
    flight_options = flights.get_direct_flights_from_origin_to_desintaion(
        origin, dest, departure_date, return_date, travellers, currency)
    return flight_options


def get_accommodation_options(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency):
    accommodation_options = accommodation.get_accommodation_options(
        dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency)
    return accommodation_options
