from amadeus import Client, ResponseError, Location
import json
from config import dbManager
import os
import datetime

amadeus = Client(
    hostname='production',
    log_level="debug"
)


def get_accommodation_for_destination(dest, check_in_date, check_out_date):
    # accommodation = amadeus.shopping.hotel_offers.get(
    #     cityCode=dest, checkInDate=check_in_date, checkOutDate=check_out_date).result
    # f = open("data/hotels_spec_data.txt", "w")
    # f.write(json.dumps(accommodation))
    # f.close()
    f = open("data/hotels_spec_data.txt", "r")
    accommodation = json.loads(f.read())
    f.close()
    selected_accommodation = get_accommodation_details(accommodation)
    return selected_accommodation


def get_accommodation_details(accommodation):
    selected_accommodation = {}
    chosen_accommodation = accommodation["data"][2]
    selected_accommodation["type"] = chosen_accommodation["hotel"]["type"]
    selected_accommodation["name"] = chosen_accommodation["hotel"]["name"]
    selected_accommodation["stars"] = int(
        chosen_accommodation["hotel"]["rating"])
    selected_accommodation["id"] = chosen_accommodation["hotel"]["hotelId"]
    selected_accommodation["latitude"] = chosen_accommodation["hotel"]["latitude"]
    selected_accommodation["longitude"] = chosen_accommodation["hotel"]["longitude"]
    selected_accommodation["image_url"] = chosen_accommodation["hotel"]["media"][0]["uri"]
    symbol = dbManager.query("""
    SELECT symbol FROM currency WHERE id = \"{currency_id}\"
    """.format(currency_id=chosen_accommodation["offers"][0]["price"]["currency"]))[0][0]
    selected_accommodation["price"] = {"amount": float(chosen_accommodation["offers"][0]["price"]
                                                       ["total"]), "currency": chosen_accommodation["offers"][0]["price"]["currency"], "symbol": symbol}
    return selected_accommodation


def get_direct_flights_from_origin_to_desintaion(origin, dest, departure_date, return_date, travellers):
    # flights = amadeus.shopping.flight_offers_search.get(
    #     originLocationCode=origin, destinationLocationCode=dest, departureDate=departure_date, returnDate=return_date, adults=travellers["adults"], nonStop="true").result
    # f = open("data/flights_spec_data.txt", "w")
    # f.write(json.dumps(flights) + "\n")
    # f.close()
    f = open("data/flights_spec_data.txt", "r")
    flights = json.loads(f.read())
    f.close()
    selected_flights = {}
    selected_flights["outbound"] = get_flight_details(flights, 0)
    selected_flights["return"] = get_flight_details(flights, 1)
    return selected_flights


def get_flight_details(flights, journey):
    selected_flights = {}
    flight_segments = flights["data"][0]["itineraries"][journey]["segments"][0]
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
    travaler_pricings = flights["data"][0]["travelerPricings"][0]
    symbol = dbManager.query("""
    SELECT symbol FROM currency WHERE id = \"{currency_id}\"
    """.format(currency_id=flights["data"][0]["price"]["currency"]))[0][0]
    selected_flights["price"] = {
        "amount": float(flights["data"][0]["price"]["total"]), "currency": flights["data"][0]["price"]["currency"], "symbol": symbol}
    selected_flights["class"] = travaler_pricings["fareDetailsBySegment"][0]["cabin"]
    return selected_flights


def get_flight_date_and_time(at):
    date_time = datetime.datetime.strptime(
        at, '%Y-%m-%dT%H:%M:%S')
    date = date_time.strftime("%d %B")
    time = date_time.strftime("%H:%M")
    return date, time


def getAllDirectFlights(origin, date):
    # flights = amadeus.shopping.flight_destinations.get(
    #     origin=origin, departureDate=date, duration=3).result
    # f = open("flights_data.txt", "w")
    # f.write(json.dumps(flights))
    # f.close()
    f = open("data/flights_data.txt", "r")
    flights = json.loads(f.read())
    f.close()

    results = parseFlights(flights)
    return results


def parseFlights(flights):
    results = []
    currency = flights["meta"]["currency"]
    for i in range(0, len(flights["data"])):
        notFound = False
        code = flights["data"][i]["destination"]
        type = flights["dictionaries"]["locations"][code]["subType"]
        if type == "CITY":
            name = flights["dictionaries"]["locations"][code]["detailedName"]
        elif type == "AIRPORT":
            name = dbManager.query(
                "SELECT city FROM airport WHERE iata = \"" + code + "\"")
            if (len(name) > 0):
                name = name[0][0]
            else:
                print("NOT FOUND: " + code)
                notFound = True
        if not notFound:
            amount = flights["data"][i]["price"]["total"]
            destId = dbManager.query("""
            SELECT d.id FROM (
                SELECT destination_name.name, MAX(destination.population) as maxPop FROM 
                    destination_name JOIN destination ON destination_name.geonameid = destination.id
                WHERE destination_name.name = "{name}" GROUP BY destination_name.name
            ) as x INNER JOIN destination_name as dn ON dn.name = x.name JOIN destination as d 
            on d.population = x.maxPop AND dn.geonameid = d.id GROUP BY d.id;
            """ .format(name=name))
            if len(destId) > 0:
                destId = destId[0][0]
            else:
                notFound = True
        if not notFound:
            results.append(
                {"id": destId, "name": name, "price": {"currency": currency, "amount": amount}})
    return results
