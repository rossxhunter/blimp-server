from config import db_manager
from apis import exchange_rates, amadeus
from util import util
from datetime import datetime, timedelta
import json
import re
import json


def get_accommodation_options(dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency):

    timestamp = datetime.now()
    timestamp_hour_ago = timestamp - timedelta(hours=6)

    cache_query = db_manager.query("""
    SELECT result FROM accommodation_result
    WHERE dest = "{dest}" AND check_in_date = "{check_in_date}" AND check_out_date = "{check_out_date}" AND travellers = "{travellers}" AND currency = "{currency}"
    AND timestamp > "{timestamp_hour_ago}"
    """.format(dest=dest, check_in_date=check_in_date, check_out_date=check_out_date, travellers=str(travellers), currency=currency, timestamp_hour_ago=timestamp_hour_ago))

    if len(cache_query) != 0:
        accommodation_details = json.loads(cache_query[0][0])
    else:
        accommodation_options = amadeus.get_accommodation_for_destination(
            dest, check_in_date, check_out_date, travellers, accommodation_type, accommodation_stars, accommodation_amenities, currency, [], None)

        dep_date_dt = datetime.strptime(check_in_date, '%Y-%m-%d')
        ret_date_dt = datetime.strptime(check_out_date, '%Y-%m-%d')
        nights = (ret_date_dt - dep_date_dt).days

        accommodation_details = []
        rates = {}
        i = 0
        for acc in accommodation_options:
            if "rating" in acc["hotel"] and int(acc["hotel"]["rating"]) >= accommodation_stars:
                conversion = get_exchange_rate_for_accommodation(
                    acc["offers"][0]["price"]["currency"], currency, rates)
                if conversion == None:
                    return []
                details = get_accommodation_details(acc, currency, conversion)
                if details != None:
                    details["id"] = i
                    details["nights"] = nights
                    accommodation_details.append(details)
                    db_manager.insert("""
                    INSERT INTO hotel (id, provider, city, name, latitude, longitude, chain_code, stars, street_address, postcode, amenities, images_fetched)
                    VALUES ("{hotel_id}", "amadeus", "{dest}", "{name}", {latitude}, {longitude}, NULL, {stars}, "{street_address}", "{postcode}", "{amenities}", FALSE)
                    """.format(hotel_id=details["hotelId"], dest=dest, name=details["name"], latitude=details["latitude"], longitude=details["longitude"], stars=details["stars"], street_address=details["address"]["streetAddress"].replace('\\n', '\\\\n'), postcode=details["address"]["postcode"], amenities=json.dumps(details["amenities"]).replace('"', '\\"')))

                i += 1
        db_manager.insert("""
        REPLACE INTO accommodation_result (dest, check_in_date, check_out_date, travellers, currency, result, timestamp)
        VALUES ("{dest}", "{check_in_date}", "{check_out_date}", "{travellers}", "{currency}", "{result}", "{timestamp}")
        """.format(dest=dest, check_in_date=check_in_date, check_out_date=check_out_date, travellers=travellers, currency=currency, timestamp=timestamp, result=json.dumps(accommodation_details, ensure_ascii=False).replace('\\n', '\\\\n').replace('\\r', '\\\\r').replace('"', '\\"')))
    for hotel in accommodation_details:
        hotel_images = db_manager.query("""
        SELECT url
        FROM hotel_photo
        WHERE hotel_id = "{hotel}"
        """.format(hotel=hotel["hotelId"]))
        if len(hotel_images) > 0:
            hotel["images"] = []
        for image in hotel_images:
            hotel["images"].append(image[0])

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
    accommodation_details["description"] = accommodation["hotel"]["description"]["text"].replace(
        '"', '') if "description" in accommodation["hotel"] else None
    accommodation_details["amenities"] = get_accommodation_amenities(
        accommodation["hotel"]["amenities"])
    accommodation_details["address"] = {}
    street_address = ""
    for line in accommodation["hotel"]["address"]["lines"]:
        street_address += line + "\n"
    accommodation_details["address"]["streetAddress"] = street_address
    accommodation_details["address"]["postcode"] = accommodation["hotel"]["address"][
        "postalCode"] if "postalCode" in accommodation["hotel"]["address"] else None
    images, rating = get_accommodation_images_and_rating(
        accommodation["hotel"])
    accommodation_details["images"] = images
    if rating != None:
        accommodation_details["rating"] = rating
    # returned_currency = cheapest_offer["price"]["currency"]

    accommodation_details["offers"] = []
    cheapest_price = float(accommodation["offers"][0]["price"]["total"])
    for offer in accommodation["offers"]:
        acc_offer = {}
        room_type = get_room_type(offer["room"]["type"])
        if room_type == None:
            return None
        acc_offer["roomType"] = room_type
        acc_offer["roomType"]["category"] = offer["room"]["typeEstimated"]["category"] if "typeEstimated" in offer["room"] and "category" in offer["room"]["typeEstimated"] else None
        acc_offer["roomType"]["estimatedBedType"] = offer["room"]["typeEstimated"][
            "bedType"] if "typeEstimated" in offer["room"] and "bedType" in offer["room"]["typeEstimated"] else None
        acc_offer["boardType"] = get_board_type(
            offer["boardType"] if "boardType" in offer else "ROOM_ONLY")
        if "total" in offer["price"]:
            price_amount = float(
                offer["price"]["total"]) * conversion
        else:
            price_amount = float(
                offer["price"]["base"]) * conversion

        acc_offer["price"] = {"amount": float(
            price_amount), "currency": currency}
        acc_offer["id"] = offer["id"]
        if price_amount <= cheapest_price:
            cheapest_price = price_amount
            accommodation_details["selectedOffer"] = acc_offer
        acc_offer["description"] = offer["room"]["description"]
        accommodation_details["offers"].append(acc_offer)
    accommodation_details["offers"] = sorted(
        accommodation_details["offers"], key=lambda o: o['price']["amount"])
    accommodation_details["hotelDistance"] = accommodation["hotel"]["hotelDistance"]
    accommodation_details["cheapestPrice"] = cheapest_price
    return accommodation_details


def get_board_type(raw_board_type):
    return raw_board_type.title().replace("_", " ").replace("-", " ")


def get_accommodation_amenities(raw_amenities):
    # amenity_map = {"RESTAURANT": "Restaurant", "MASSAGE": "Massage", "SWIMMING_POOL": "Swimming Pool", "SPA": "Spa", "FITNESS_CENTER": "Fitness Center", "AIR_CONDITIONING": "Air Conditioning", "RESTAURANT": "Restaurant", PARKING, PETS_ALLOWED, AIRPORT_SHUTTLE, BUSINESS_CENTER, DISABLED_FACILITIES, WIFI, MEETING_ROOMS, NO_KID_ALLOWED, TENNIS, GOLF, KITCHEN, ANIMAL_WATCHING, BABY-SITTING, BEACH, CASINO, JACUZZI, SAUNA, SOLARIUM, MASSAGE, VALET_PARKING, BAR, KIDS_WELCOME, NO_PORN_FILMS, MINIBAR, TELEVISION, WI-FI_IN_ROOM, ROOM_SERVICE, GUARDED_PARKG}
    amenities = []
    # for a in raw_amenities:
    #     if a in amenity_map:
    #         amenities.append(amenity_map[a])
    for a in raw_amenities:
        if a == "WI-FI_IN_ROOM":
            amenities.append("Wifi in Room")
        elif a == "GUARDED_PARKG":
            amenities.append("Guarded Parking")
        elif a == "NO_KID_ALLOWED":
            amenities.append("No Kids Allowed")
        else:
            amenities.append(a.title().replace("_", " ").replace("-", " "))
    return amenities


def get_room_type(type):
    if type == "SUP":
        return {"bedType": "Queen", "numBeds": 1}
    elif type == "D1R":
        return {"bedType": "Double", "numBeds": 1}
    elif type == "ROH":
        return {"bedType": "Run of House", "numBeds": 1}
    elif type == "TWN":
        return {"bedType": "Twin", "numBeds": 2}
    elif not re.search("^[A-KNPS-UW][0-9\*][TSDKQWP\*]$", type):
        print("Invalid format: " + type)
        return None
    else:
        if type[1:3] == "2T":
            return {"bedType": "Twin", "numBeds": 2}
        elif type[1:3] == "2*":
            return {"bedType": "Twin/Double", "numBeds": None}
        elif type[1:3] == "2D":
            return {"bedType": "Double", "numBeds": 1}
        elif type[1:3] == "1T":
            return {"bedType": "Twin", "numBeds": 2}
        else:
            bed_type_code = type[2]
            bedType = get_bed_type(bed_type_code)
            # if bedType == None:
            #     print("Invalid bed type: " + type)
            #     return None
            numBeds = None
            if type[1] != "*":
                numBeds = type[1]
            return {"bedType": bedType, "numBeds": numBeds}


def get_bed_type(bed_type_code):
    if bed_type_code == "Q":
        return "Queen"
    elif bed_type_code == "K":
        return "King"
    elif bed_type_code == "W":
        return "Water"
    elif bed_type_code == "P":
        return "Pull Out"
    elif bed_type_code == "S":
        return "Single"
    elif bed_type_code == "D":
        return "Double"
    elif bed_type_code == "T":
        return "Twin"
    elif bed_type_code == "*":
        return "Unknown"
    return None


def get_accommodation_images_and_rating(acc):
    default_images = []
    if "media" in acc:
        for im in acc["media"]:
            new_uri = im["uri"].replace("http://", "https://")
            s = re.search('cloudfront.net/(.*)/', new_uri)
            if s != None:
                new_uri = new_uri.replace("B.JPEG", s.group(1) + ".JPEG")
            default_images.append(new_uri)
    hotel_id = acc["hotelId"]
    hotel_details = db_manager.query("""
    SELECT overall, sleep_quality, service, facilities, room_comforts, value_for_money, catering, swimming_pool, location, internet, points_of_interest, staff
    FROM hotel_rating
    WHERE hotel = "{hotel_id}"
    """.format(hotel_id=hotel_id))
    if len(hotel_details) == 0:
        return default_images, None
    rating = {"overall": hotel_details[0][0], "sleep_quality": hotel_details[0][1], "service": hotel_details[0][2], "facilities": hotel_details[0][3], "room_comforts": hotel_details[0][4], "value_for_money": hotel_details[0]
              [5], "catering": hotel_details[0][6], "swimming_pool": hotel_details[0][7], "location": hotel_details[0][8], "internet": hotel_details[0][9], "points_of_interest": hotel_details[0][10], "staff": hotel_details[0][11]}
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
