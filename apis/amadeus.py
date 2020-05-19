from amadeus import Client, ResponseError, Location
import json
from config import db_manager
import os
from datetime import datetime, timedelta
from util.util import list_to_str_no_brackets
from apis import exchange_rates
from util.exceptions import NoResults

amadeus = Client(
    hostname='production',
    # log_level="debug"
)


def get_accommodation_for_destination(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency):
    if accommodation_stars == 1:
        accommodation_stars_range = [1, 2, 3, 4]
    else:
        accommodation_stars_range = list(range(accommodation_stars, 6))
    accommodation = amadeus.shopping.hotel_offers.get(
        view="FULL", cityCode=dest, checkInDate=check_in_date, checkOutDate=check_out_date, adults=travellers["adults"], sort="PRICE", currency=currency).result
    # f = open("data/hotels_spec_data.txt", "w")
    # f.write(json.dumps(accommodation))
    # f.close()
    # f = open("data/hotels_spec_data.txt", "r")
    # accommodation = json.loads(f.read())
    # f.close()
    return accommodation


def get_direct_flights_from_origin_to_desintaion(origin, dest, departure_date, return_date, travellers, currency):
    flights = amadeus.shopping.flight_offers_search.get(
        originLocationCode=origin, destinationLocationCode=dest, departureDate=departure_date, returnDate=return_date, adults=travellers["adults"], nonStop="true", currencyCode=currency).result

    # f = open("data/flights_spec_data.txt", "w")
    # f.write(json.dumps(flights) + "\n")
    # f.close()
    # f = open("data/flights_spec_data.txt", "r")
    # flights = json.loads(f.read())
    # f.close()
    return flights


def get_all_one_way_flights(origin, departure_date):
    flights = amadeus.shopping.flight_destinations.get(
        origin=origin, departureDate=departure_date, oneWay=True).result

    return flights


def get_all_return_flights(origin, departure_date, return_date):

    dep_date_dt = datetime.strptime(departure_date, '%Y-%m-%d')
    dep_date_dt_plus_1 = dep_date_dt + timedelta(days=1)
    dep_date_plus_1_str = datetime.strftime(dep_date_dt_plus_1, '%Y-%m-%d')
    ret_date_dt = datetime.strptime(return_date, '%Y-%m-%d')
    duration = (ret_date_dt - dep_date_dt).days

    flights = amadeus.shopping.flight_destinations.get(
        origin=origin, departureDate=departure_date, duration=duration, nonStop="true").result
    # f = open("flights_data.txt", "w")
    # f.write(json.dumps(flights))
    # f.close()
    # f = open("data/flights_data.txt", "r")
    # flights = json.loads(f.read())
    # f.close()

    return flights
