from config import db_manager
from _datetime import datetime
from apis.exchange_rates import get_exchange_rate
from apis import musement


def get_attractions(city):
    attractions_query = db_manager.query("""
    SELECT poi.id, poi.name, categories.name, categories.icon_prefix, poi_photo.url, poi.rating, poi.latitude, poi.longitude
    FROM poi
    JOIN poi_photo ON poi_photo.reference = (
        SELECT p.reference FROM poi_photo AS p
        WHERE p.poi_id = poi.id
        LIMIT 1
    )
    JOIN categories ON categories.id = foursquare_category_id
    WHERE poi.destination_id = {city}
    ORDER BY poi.num_ratings DESC
    """.format(city=city))
    attractions = []
    for attraction in attractions_query:
        attractions.append(
            {"id": attraction[0],  "name": attraction[1], "category": attraction[2], "categoryIcon": attraction[3], "images": [attraction[4]], "rating": attraction[5], "description": ""})
    return attractions


def get_valid_dates(origin, city, currency):
    valid_dates_query = db_manager.query("""
    SELECT departure_date, return_date, price_amount, price_currency
    FROM flyable_destination
    WHERE origin = {origin} AND destination = {destination} AND departure_date >= "{today_date}"
    """.format(origin=origin, destination=city, today_date=datetime.now()))
    valid_dates = []
    if len(valid_dates_query) > 0:
        conversion_rate = get_exchange_rate(valid_dates_query[0][3], currency)
        for vd in valid_dates_query:
            price = vd[2] * conversion_rate
            valid_dates.append(
                {"departureDate": vd[0].strftime("%Y-%m-%d"), "returnDate": vd[1].strftime("%Y-%m-%d"), "price": price})
    return valid_dates


def fetch_activity_details(activity_id):
    activity = db_manager.query("""
        SELECT poi.name, destination.name, country_code, poi.latitude, poi.longitude, poi.rating, categories.name,categories.icon_prefix,categories.average_time_spent_minutes, poi.wiki_description
        FROM poi
        JOIN destination ON destination.id = poi.destination_id
        JOIN categories ON categories.id = poi.foursquare_category_id
        WHERE poi.id = "{poi_id}"
        """.format(poi_id=activity_id))[0]
    images = db_manager.query("""
        SELECT url
        FROM poi_photo
        WHERE poi_id = "{poi_id}"
        """.format(poi_id=activity_id))
    activity_images = []
    for image in images:
        activity_images.append(image[0])
    details = {"id": activity_id, "name": activity[0], "cityName": activity[1], "countryCode": activity[2], "latitude": activity[3], "longitude": activity[4],
               "rating": activity[5], "category": activity[6], "categoryIcon": activity[7], "timeSpent": activity[8], "description": activity[9], "images": activity_images}

    return details
