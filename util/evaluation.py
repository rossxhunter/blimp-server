from config import db_manager
from util.util import list_to_str_no_brackets_add_speech_marks
from core import itinerary


def get_poi_details_for_itinerary(itinerary):
    poi_ids = []
    for day in itinerary.items():
        for poi in day[1]:
            poi_ids.append(poi["id"])

    if len(poi_ids) == 0:
        return {}

    details_query = db_manager.query("""
    SELECT poi.id, poi.name, rating, num_ratings, url, wiki_description, categories.name, categories.icon_prefix
    FROM poi
    JOIN poi_photo ON poi_photo.poi_id = poi.id
    JOIN categories ON categories.id = poi.foursquare_category_id
    WHERE poi.id IN ({poi_ids})
    """.format(poi_ids=list_to_str_no_brackets_add_speech_marks(poi_ids)))
    poi_details = {}
    for poi in details_query:
        poi_details[poi[0]] = poi

    itinerary_with_details = {}
    for day in itinerary.items():
        for poi in day[1]:
            details = poi_details[poi["id"]]
            if day[0] not in itinerary_with_details:
                itinerary_with_details[day[0]] = []
            itinerary_with_details[day[0]].append({"id": poi["id"], "startTime": poi["startTime"], "duration": poi["duration"], "travelTimeToNext": poi["travelTimeToNext"], "travelMethodToNext": poi["travelMethodToNext"], "name": details[1], "rating": details[2], "popularity": details[3],
                                                   "images": [details[4]], "description": details[5], "category": details[6], "categoryIcon": details[7]})

    return itinerary_with_details


def get_external_itinerary(provider, dest_id):
    itinerary_elements = db_manager.query("""
    SELECT poi_id, day, start_time, duration, travel_time_to_next, travel_method_to_next
    FROM external_itinerary
    WHERE destination_id = {dest_id} AND provider = "{provider}"
    ORDER BY day, start_time
    """.format(dest_id=dest_id, provider=provider))
    itin = {}
    for elem in itinerary_elements:
        if elem[1] not in itin:
            itin[elem[1]] = []
        itin[elem[1]].append(
            {"id": elem[0], "startTime": elem[2], "duration": elem[3], "travelTimeToNext": elem[4], "travelMethodToNext": elem[5]})
    timed_itinerary = {}
    for day in itin.items():
        timed_itinerary[day[0]] = itinerary.calculate_itinerary_for_evaluation(
            dest_id, 3, poi_order=day[1], day=day[0], window=[8, 22])[0]
    return timed_itinerary
