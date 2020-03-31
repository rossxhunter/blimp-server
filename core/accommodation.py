from config import db_manager
from apis import exchange_rates, amadeus
from util import util


def get_accommodation_options(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency):

    accommodation_options = amadeus.get_accommodation_for_destination(
        dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency)

    accommodation_details = []
    rates = {}
    for acc in accommodation_options["data"]:
        conversion = get_exchange_rate_for_accommodation(
            acc["offers"][0]["price"]["currency"], currency, rates)

        details = get_accommodation_details(acc, currency, conversion)
        accommodation_details.append(details)
    return accommodation_details


def get_exchange_rate_for_accommodation(returned_currency, currency, rates):
    conversion = 1
    if returned_currency != currency:
        if (returned_currency, currency) in rates:
            conversion = rates[(
                returned_currency, currency)]
        else:
            conversion = exchange_rates.get_exchange_rate(
                returned_currency, currency)
            rates[(returned_currency, currency)] = conversion
    return conversion


def cache_accommodation_options(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_ratings, accommodation_amenities, currency, response):
    # print("""
    # INSERT INTO hotel_request (city_code, check_in_date, check_out_date, adults, amenities, ratings, currency) VALUES ({city_code}, {check_in_date}, {check_out_date}, {adults}, {amenities}, {ratings}, {currency})
    # """.format(city_code=dest, check_in_date=check_in_date, check_out_date=check_out_date, adults=travellers["adults"], amenities=util.list_to_str_no_brackets(accommodation_amenities), ratings=accommodation_ratings, currency=currency))
    response_escaped = str(response).translate(str.maketrans({"\"":  r"\\\""}))
    db_manager.insert("""
    INSERT INTO hotel_request (city_code, check_in_date, check_out_date, adults, amenities, ratings, currency, response) VALUES ("{city_code}", "{check_in_date}", "{check_out_date}", {adults}, "{amenities}", {ratings}, "{currency}", "{response}")
    """.format(city_code=dest, check_in_date=check_in_date, check_out_date=check_out_date, adults=travellers["adults"], amenities=util.list_to_str_no_brackets(accommodation_amenities), ratings=accommodation_ratings, currency=currency, response=response_escaped))


def get_accommodation_details(accommodation, currency, conversion):
    accommodation_details = {}
    accommodation_details["type"] = accommodation["hotel"]["type"]
    accommodation_details["name"] = accommodation["hotel"]["name"]
    accommodation_details["stars"] = int(accommodation["hotel"]["rating"])
    accommodation_details["id"] = accommodation["hotel"]["hotelId"]
    accommodation_details["latitude"] = accommodation["hotel"]["latitude"]
    accommodation_details["longitude"] = accommodation["hotel"]["longitude"]
    if "media" in accommodation["hotel"]:
        accommodation_details["image_url"] = accommodation["hotel"]["media"][0]["uri"]

    returned_currency = accommodation["offers"][0]["price"]["currency"]

    if "total" in accommodation["offers"][0]["price"]:
        price_amount = float(
            accommodation["offers"][0]["price"]["total"]) * conversion
    else:
        price_amount = float(
            accommodation["offers"][0]["price"]["base"]) * conversion
    accommodation_details["price"] = {"amount": float(
        price_amount), "currency": currency}

    return accommodation_details
