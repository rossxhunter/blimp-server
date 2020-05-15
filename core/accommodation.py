from config import db_manager
from apis import exchange_rates, amadeus
from util import util
from datetime import datetime, timedelta
import json


def get_accommodation_options(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency):

    timestamp = datetime.now()
    timestamp_hour_ago = timestamp - timedelta(hours=1)

    cache_query = db_manager.query("""
    SELECT result FROM accommodation_result
    WHERE dest = "{dest}" AND check_in_date = "{check_in_date}" AND check_out_date = "{check_out_date}" AND travellers = "{travellers}" AND currency = "{currency}"
    AND timestamp > "{timestamp_hour_ago}"
    """.format(dest=dest, check_in_date=check_in_date, check_out_date=check_out_date, travellers=str(travellers), currency=currency, timestamp_hour_ago=timestamp_hour_ago))

    if len(cache_query) != 0:
        accommodation_details = eval(cache_query[0][0])
    else:
        accommodation_options = amadeus.get_accommodation_for_destination(
            dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency)

        dep_date_dt = datetime.strptime(check_in_date, '%Y-%m-%d')
        ret_date_dt = datetime.strptime(check_out_date, '%Y-%m-%d')
        nights = (ret_date_dt - dep_date_dt).days

        accommodation_details = []
        rates = {}
        i = 0
        for acc in accommodation_options["data"]:
            if "rating" in acc["hotel"] and int(acc["hotel"]["rating"]) >= accommodation_stars:
                conversion = get_exchange_rate_for_accommodation(
                    acc["offers"][0]["price"]["currency"], currency, rates)

                details = get_accommodation_details(acc, currency, conversion)
                details["id"] = i
                details["nights"] = nights
                accommodation_details.append(details)
                i += 1

        db_manager.insert("""
        REPLACE INTO accommodation_result (dest, check_in_date, check_out_date, travellers, currency, result, timestamp)
        VALUES ("{dest}", "{check_in_date}", "{check_out_date}", "{travellers}", "{currency}", "{result}", "{timestamp}")
        """.format(dest=dest, check_in_date=check_in_date, check_out_date=check_out_date, travellers=travellers, currency=currency, timestamp=timestamp, result=str(accommodation_details)))

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
    response_escaped = str(response).translate(str.maketrans({"\"":  r"\\\""}))
    db_manager.insert("""
    INSERT INTO hotel_request (city_code, check_in_date, check_out_date, adults, amenities, ratings, currency, response) VALUES ("{city_code}", "{check_in_date}", "{check_out_date}", {adults}, "{amenities}", {ratings}, "{currency}", "{response}")
    """.format(city_code=dest, check_in_date=check_in_date, check_out_date=check_out_date, adults=travellers["adults"], amenities=util.list_to_str_no_brackets(accommodation_amenities), ratings=accommodation_ratings, currency=currency, response=response_escaped))


def get_accommodation_details(accommodation, currency, conversion):
    accommodation_details = {}
    accommodation_details["type"] = accommodation["hotel"]["type"]
    accommodation_details["name"] = accommodation["hotel"]["name"]
    accommodation_details["stars"] = int(accommodation["hotel"]["rating"])
    accommodation_details["hotelId"] = accommodation["hotel"]["hotelId"]
    accommodation_details["latitude"] = accommodation["hotel"]["latitude"]
    accommodation_details["longitude"] = accommodation["hotel"]["longitude"]

    accommodation_details["images"], accommodation_details["rating"] = get_accommodation_images_and_rating(
        accommodation["hotel"])

    returned_currency = accommodation["offers"][0]["price"]["currency"]

    if "total" in accommodation["offers"][0]["price"]:
        price_amount = float(
            accommodation["offers"][0]["price"]["total"]) * conversion
    else:
        price_amount = float(
            accommodation["offers"][0]["price"]["base"]) * conversion
    accommodation_details["price"] = {"amount": float(
        price_amount), "currency": currency}

    if "typeEstimated" in accommodation["offers"][0]["room"]:
        room_type = accommodation["offers"][0]["room"]["typeEstimated"]
        accommodation_details["roomType"] = room_type

    accommodation_details["hotelDistance"] = accommodation["hotel"]["hotelDistance"]

    return accommodation_details


def get_accommodation_images_and_rating(acc):
    default_images = []
    if "media" in acc:
        default_images = [acc["media"][0]["uri"]]
    hotel_id = acc["hotelId"]
    hotel_details = db_manager.query("""
    SELECT rating
    FROM hotel
    WHERE is_correct = 1 AND id = "{hotel_id}"
    """.format(hotel_id=hotel_id))
    if len(hotel_details) == 0:
        return default_images, None
    rating = hotel_details[0][0]
    hotel_photos = db_manager.query("""
    SELECT url FROM hotel_photo
    WHERE hotel_id = "{hotel_id}" AND url IS NOT NULL
    """.format(hotel_id=hotel_id))
    images = []
    for photo in hotel_photos:
        images.append(photo[0])
    if len(images) == 0:
        return default_images, rating
    return images, rating
