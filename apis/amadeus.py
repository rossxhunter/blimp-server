from amadeus import Client, ResponseError, Location
import json
from config import db_manager
import os
from datetime import datetime, timedelta
from util.util import list_to_str_no_brackets
from apis import exchange_rates
from util.exceptions import NoResults
import requests

amadeus = Client(
    hostname='production',
    # log_level="debug"
)


def get_accommodation_for_destination(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency, acc_list, next_token):
    if accommodation_stars == 1:
        accommodation_stars_range = [1, 2, 3, 4]
    else:
        accommodation_stars_range = list(range(accommodation_stars, 6))
    if next_token == None:
        accommodation = amadeus.shopping.hotel_offers.get(view="FULL", cityCode=dest, checkInDate=check_in_date, checkOutDate=check_out_date,
                                                          includeClosed="false", adults=travellers["adults"], currency=currency).result
    else:
        accommodation = amadeus.shopping.hotel_offers.get(view="FULL", cityCode=dest, checkInDate=check_in_date, checkOutDate=check_out_date,
                                                          includeClosed="false", adults=travellers["adults"], currency=currency, page={"offset": next_token}).result
    acc_list.extend(accommodation["data"])
    if "meta" in accommodation and "links" in accommodation["meta"] and "next" in accommodation["meta"]["links"]:
        current_next_token = accommodation["meta"]["links"]["next"].split(
            "page[offset]=", 1)[1]
        return get_accommodation_for_destination(dest, check_in_date, check_out_date, travellers,
                                                 accommodation_type, accommodation_stars, accommodation_amenities, currency, acc_list, current_next_token)
    return acc_list


def get_direct_flights_from_origin_to_desintaion(origin, dest, departure_date, return_date, travellers, currency):
    flights = amadeus.shopping.flight_offers_search.get(
        originLocationCode=origin, destinationLocationCode=dest, departureDate=departure_date, returnDate=return_date, adults=travellers["adults"], children=travellers["children"], infants=travellers["infants"], nonStop="true", currencyCode=currency).result

    return flights


def get_all_one_way_flights(origin, departure_date):
    flights = amadeus.shopping.flight_destinations.get(
        origin=origin, departureDate=departure_date, oneWay=True).result

    return flights


def get_all_return_flights(origin, departure_date, duration):

    flights = amadeus.shopping.flight_destinations.get(
        origin=origin, departureDate=departure_date, duration=duration, nonStop="true", viewBy="DURATION").result

    return flights


def get_cheapest_return_flights(origin, destination, departure_date, return_date):

    dep_date_dt = datetime.strptime(departure_date, '%Y-%m-%d')
    dep_date_dt_plus_1 = dep_date_dt + timedelta(days=1)
    dep_date_plus_1_str = datetime.strftime(dep_date_dt_plus_1, '%Y-%m-%d')
    ret_date_dt = datetime.strptime(return_date, '%Y-%m-%d')
    duration = (ret_date_dt - dep_date_dt).days

    flights = amadeus.shopping.flight_dates.get(
        origin=origin, destination=destination, departureDate=departure_date, duration=duration, nonStop="true").result

    return flights
