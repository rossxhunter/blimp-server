from config import db_manager
from apis import amadeus
from datetime import datetime
from util.util import list_to_tuple


def get_all_return_flights(origin, departure_date, return_date):
    flights = amadeus.get_all_return_flights(
        origin, departure_date, return_date)
    return parse_flights(flights)


def get_all_one_way_flights(origin, departure_date, return_date):
    flights = amadeus.get_all_one_way_flights(origin, departure_date)
    return parse_flights(flights)


def get_direct_flights_from_origin_to_desintaion(origin, dest, departure_date, return_date, travellers, currency):
    flights = amadeus.get_direct_flights_from_origin_to_desintaion(
        origin, dest, departure_date, return_date, travellers, currency)
    flights_details = []
    for flight in flights["data"]:
        details = {}
        details["outbound"] = get_flight_details(flight, 0)
        details["return"] = get_flight_details(flight, 1)
        flights_details.append(details)
    return flights_details


def get_flight_details(flight, journey):
    selected_flights = {}
    flight_segments = flight["itineraries"][journey]["segments"][0]
    points = ["departure", "arrival"]
    for point in points:
        selected_flights[point] = {}
        selected_flights[point]["airportCode"] = flight_segments[point]["iataCode"]
        selected_flights[point]["terminal"] = flight_segments[point]["terminal"]
        departure_date, departure_time = get_flight_date_and_time(
            flight_segments[point]["at"])
        selected_flights[point]["date"] = departure_date
        selected_flights[point]["time"] = departure_time
    selected_flights["carrierCode"] = flight_segments["carrierCode"]
    selected_flights["duration"] = flight_segments["duration"]
    travaler_pricings = flight["travelerPricings"][0]
    selected_flights["price"] = {
        "amount": float(flight["price"]["total"])/2, "currency": flight["price"]["currency"]}
    selected_flights["class"] = travaler_pricings["fareDetailsBySegment"][0]["cabin"]
    return selected_flights


def get_flight_date_and_time(at):
    date_time = datetime.strptime(
        at, '%Y-%m-%dT%H:%M:%S')
    date = date_time.strftime("%d %B")
    time = date_time.strftime("%H:%M")
    return date, time


def parse_flights(flights):
    results = {}
    currency = flights["meta"]["currency"]
    names = {}
    city_codes = {}
    airport_codes = {}
    flights_data = flights["data"]
    for i in range(0, len(flights_data)):
        code = flights["data"][i]["destination"]
        type = flights["dictionaries"]["locations"][code]["subType"]
        if type == "CITY":
            city_codes[code] = i
        elif type == "AIRPORT":
            airport_codes[code] = i

    dests_for_city_codes = db_manager.query("""
    SELECT city_code, id, name FROM destination WHERE city_code IN {city_codes}
    """.format(city_codes=list_to_tuple(city_codes.keys())))

    dests_for_airport_codes = db_manager.query("""
    SELECT airports.iata_code, destination.id, destination.name
    FROM destination
    JOIN airports ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
    WHERE airports.iata_code IN {airport_codes}
    """.format(airport_codes=list_to_tuple(airport_codes.keys())))

    codes = [(dests_for_city_codes, city_codes),
             (dests_for_airport_codes, airport_codes)]
    for c in codes:
        for dest in c[0]:
            if len(dest) > 0:
                dest_id = dest[1]
                dest_name = dest[2]
                amount = flights_data[c[1][dest[0]]]["price"]["total"]
                results[dest_id] = {"name": dest_name, "price": {
                    "currency": currency, "amount": amount}}
            else:
                print("NOT FOUND: " + dest[0])
    return results
