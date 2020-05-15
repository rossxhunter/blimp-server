from config import db_manager
from apis import amadeus
from datetime import datetime, timedelta
from util.util import list_to_tuple
import dateutil.parser
import re
from geopy import distance


def get_all_return_flights(origin, departure_date, return_date):

    origin_id = db_manager.query("""
    SELECT id FROM destination WHERE city_code = "{origin}"
    ORDER BY population DESC LIMIT 1
    """.format(origin=origin))[0][0]

    cache_query = db_manager.query("""
    SELECT destination, name, price_amount, price_currency FROM flyable_destination
    WHERE origin = {origin_id} AND departure_date = "{departure_date}" AND return_date = "{return_date}" 
    """.format(origin_id=origin_id, departure_date=departure_date, return_date=return_date))

    parsed_flights = {}

    for d in cache_query:
        parsed_flights[d[0]] = {"name": d[1], "price": {
            "amount": d[2], "currency": d[3]}}

    if len(cache_query) == 0:
        flights = amadeus.get_all_return_flights(
            origin, departure_date, return_date)
        parsed_flights = parse_flights(flights)
        for flight in parsed_flights.items():
            db_manager.insert("""
            REPLACE INTO flyable_destination (origin, destination, departure_date, return_date, name, price_amount, price_currency)
            VALUES ({origin_id}, {destination}, "{departure_date}",
                    "{return_date}", "{name}", {price_amount}, "{price_currency}")
            """.format(origin_id=origin_id, destination=flight[0], departure_date=departure_date, return_date=return_date, name=flight[1]["name"], price_amount=flight[1]["price"]["amount"], price_currency=flight[1]["price"]["currency"]))

    return parsed_flights


def get_all_one_way_flights(origin, departure_date, return_date):
    flights = amadeus.get_all_one_way_flights(origin, departure_date)
    return parse_flights(flights)


def get_direct_flights_from_origin_to_desintaion(origin, dest, departure_date, return_date, travellers, currency):

    timestamp = datetime.now()
    timestamp_hour_ago = timestamp - timedelta(hours=1)

    cache_query = db_manager.query("""
    SELECT result FROM flights_result
    WHERE origin = "{origin}" AND destination = "{destination}" AND departure_date = "{departure_date}" AND return_date = "{return_date}" AND travellers = "{travellers}" AND currency = "{currency}"
    AND timestamp > "{timestamp_hour_ago}"
    """.format(timestamp_hour_ago=timestamp_hour_ago, origin=origin, destination=dest, departure_date=departure_date, return_date=return_date, travellers=str(travellers), currency=currency))

    if len(cache_query) != 0:
        flights_details = eval(cache_query[0][0])
    else:
        flights = amadeus.get_direct_flights_from_origin_to_desintaion(
            origin, dest, departure_date, return_date, travellers, currency)
        flights_details = []
        i = 0
        carriers = {}
        for flight in flights["data"]:
            details = {}
            details["outbound"] = get_flight_details(flight, 0, carriers)
            details["outbound"]["journey"] = "Outbound"
            details["return"] = get_flight_details(flight, 1, carriers)
            details["return"]["journey"] = "Return"
            details["price"] = {"amount": float(
                flight["price"]["total"]), "currency": flight["price"]["currency"]}
            details["id"] = i
            flights_details.append(details)
            i += 1

        db_manager.insert("""
        REPLACE INTO flights_result (origin, destination, departure_date, return_date, travellers, currency, result, timestamp)
        VALUES ("{origin}", "{destination}", "{departure_date}", "{return_date}", "{travellers}", "{currency}", "{result}", "{timestamp}")
        """.format(origin=origin, destination=dest, departure_date=departure_date, return_date=return_date, travellers=str(travellers), currency=currency, result=str(flights_details), timestamp=timestamp))

    return flights_details


def get_flight_details(flight, journey, carriers):
    selected_flights = {}
    flight_segments = flight["itineraries"][journey]["segments"][0]
    points = ["departure", "arrival"]
    for point in points:
        selected_flights[point] = {}
        selected_flights[point]["airportCode"] = flight_segments[point]["iataCode"]
        if "terminal" in flight_segments[point]:
            selected_flights[point]["terminal"] = flight_segments[point]["terminal"]
        departure_date, departure_time = get_flight_date_and_time(
            flight_segments[point]["at"])
        selected_flights[point]["date"] = departure_date
        selected_flights[point]["time"] = departure_time
    selected_flights["carrierCode"] = flight_segments["carrierCode"]
    if selected_flights["carrierCode"] in carriers:
        carrier_name, carrier_icao = carriers[selected_flights["carrierCode"]]
    else:
        carrier_name, carrier_icao = get_carrier_details(
            selected_flights["carrierCode"])
        carriers[selected_flights["carrierCode"]] = (
            carrier_name, carrier_icao)
    selected_flights["carrierName"] = carrier_name
    selected_flights["carrierLogo"] = "https://flightaware.com/images/airline_logos/90p/" + \
        carrier_icao + ".png"
    selected_flights["duration"] = parse_duration(flight_segments["duration"])
    traveller_pricings = flight["travelerPricings"][0]
    selected_flights["price"] = {
        "amount": float(flight["price"]["total"])/2, "currency": flight["price"]["currency"]}
    selected_flights["class"] = traveller_pricings["fareDetailsBySegment"][0]["cabin"]
    return selected_flights


def get_carrier_details(carrier_code):
    q = db_manager.query("""
    SELECT name, icao_code
    FROM airline
    WHERE iata_code = "{iata_code}"
    """.format(iata_code=carrier_code))
    return q[0]


def parse_duration(duration):
    hours = re.search('PT(.*)H', duration)
    if hours == None:
        hours = 0
    else:
        hours = int(hours.group(1))
    minutes = re.search('(PT(.*)H|H)(.*)M', duration)
    if minutes == None:
        minutes = 0
    else:
        minutes = int(minutes.group(3))
    return hours * 60 + minutes


def get_flight_date_and_time(at):
    date_time = datetime.strptime(
        at, '%Y-%m-%dT%H:%M:%S')
    date = date_time.strftime("%Y%m%d")
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
    SELECT airports.iata_code, destination.id, destination.name, destination.latitude, destination.longitude, airports.latitude_deg, airports.longitude_deg
    FROM destination
    JOIN airports ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
    WHERE airports.iata_code IN {airport_codes}
    """.format(airport_codes=list_to_tuple(airport_codes.keys())))
    dests_for_airport_codes = list(dests_for_airport_codes)
    # Remove duplicate destinations by finding closest destination to airport
    airport_closest_distances = {}
    for d in dests_for_airport_codes:
        airport_distance = distance.distance((d[3], d[4]), (d[5], d[6])).km
        if d[0] not in airport_closest_distances:
            airport_closest_distances[d[0]] = {
                "dest_id": d[1], "distance": airport_distance}
        elif airport_closest_distances[d[0]]["distance"] > airport_distance:
            airport_closest_distances[d[0]] = {
                "dest_id": d[1], "distance": airport_distance}

    culled_dests_for_airport_codes = []
    for d in dests_for_airport_codes:
        if airport_closest_distances[d[0]]["dest_id"] == d[1]:
            culled_dests_for_airport_codes.append(d)

    codes = [(dests_for_city_codes, city_codes),
             (culled_dests_for_airport_codes, airport_codes)]
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
