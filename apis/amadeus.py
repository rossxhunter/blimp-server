from amadeus import Client, ResponseError
import json
from config import dbManager
import os

amadeus = Client(
    client_id=os.environ["AMADEUS_CLIENT_ID"],
    client_secret=os.environ["AMADEUS_CLIENT_SECRET"],
    hostname='production'
)


def getAllDirectFlights(origin, date):
    # flights = amadeus.shopping.flight_destinations.get(
    #     origin=origin, departureDate=date).result
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
