from config import db_manager
from apis import wikipedia, exchange_rates
from flask.json import jsonify
from util.util import list_to_tuple, listToStr, get_list_of_values_from_list_of_dicts, get_origin_code
from util.exceptions import NoResults
from core import accommodation, flights
from core.flights import parse_duration
from datetime import datetime
import random

NUM_DEST_ATTEMPTS = 3


def calculate_destination(constraints, soft_prefs, pref_scores, feedback):
    dests = dests_from_constraints_recommender(constraints)
    if ("destination" in constraints):
        if (constraints["destination"]["type"] == "city"):
            dest_id, name = get_destination_from_city(
                constraints["destination"]["id"], dests)

        elif (constraints["destination"]["type"] == "airport"):
            dest_id, name = get_destination_from_airport(
                constraints["destination"]["id"])

        ranked_dests = [dest_id]

    else:
        dest_ids = dests.keys()
        dests_soft_prefs_similarities = prefs_recommender(soft_prefs, dest_ids)
        dests_pref_scores_similarities = scores_recommender(
            pref_scores, dests_soft_prefs_similarities)
        # add_to_viable_dests(
        #     dest_ids, dests_soft_prefs_similarities, dests_pref_scores_similarities)
        ranked_dests = get_ranked_dests(
            dests_soft_prefs_similarities, dests_pref_scores_similarities)

    dest_id, name, flight_options, accommodation_options = select_dest_from_ranked_dests(
        dests, ranked_dests, constraints, feedback)

    image_urls = get_dest_image_urls(dest_id)

    wiki_entry, country_code, country_name = get_dest_info(dest_id)

    month = datetime.strptime(constraints["departure_date"], "%Y-%m-%d").month

    av_temp_c, num_days_rainfall = get_dest_weather(dest_id, month)

    return {"name": name, "av_temp_c": av_temp_c, "num_days_rainfall": num_days_rainfall, "country_code": country_code, "country_name": country_name, "wiki": wiki_entry, "image_urls": image_urls, "id": dest_id, "flights": flight_options, "accommodation": accommodation_options}


def get_dest_weather(dest_id, month):
    weather_query = db_manager.query("""
    SELECT average_temp_c, num_days_rainfall
    FROM destination
    JOIN climate ON destination.weather_station_id = climate.weather_station_id
    WHERE destination.id = {dest_id} AND month = {month}
    """.format(dest_id=dest_id, month=month))
    if len(weather_query) == 0:
        return (20, 4)
    return weather_query[0]


def get_dest_info(dest_id):
    country_query = db_manager.query("""
    SELECT destination.wiki_description, country.ISO, country.Country
    FROM destination
    JOIN country ON destination.country_code = country.ISO
    WHERE destination.id = {dest_id}
    """.format(dest_id=dest_id))
    return (country_query[0][0] or "", country_query[0][1].lower(), country_query[0][2])


def get_dest_image_urls(dest_id):
    q = db_manager.query("""
    SELECT url FROM destination_photo WHERE dest_id = {dest_id} AND url IS NOT NULL
    """.format(dest_id=dest_id))
    urls = []
    for u in q:
        urls.append(u[0])
    return urls


def get_ranked_dests(dests_soft_prefs_similarities, dests_pref_scores_similarities):
    return sorted(dests_soft_prefs_similarities,
                  key=dests_soft_prefs_similarities.get, reverse=True)


def add_to_viable_dests(dests, dests_soft_prefs_similarities, dests_pref_scores_similarities):
    for dest in dests:
        viable_insert = db_manager.insert("""
        REPLACE INTO viable_destinations (id, name, soft_prefs_sim, pref_scores_sim) VALUES ({id}, (SELECT name FROM destination WHERE id = {id}), {soft_prefs_sim}, {pref_scores_sim})
        """.format(id=dest, soft_prefs_sim=dests_soft_prefs_similarities[dest], pref_scores_sim=dests_pref_scores_similarities[dest]))


def select_dest_from_ranked_dests(dests, ranked_dests, constraints, feedback):
    num_no_flights = 0
    num_feedback_invalid = 0
    num_low_budget = 0
    if feedback != None:
        ranked_dests.remove(feedback["previous_dest_id"])
    ranked_dests = ranked_dests[:10]
    random.shuffle(ranked_dests)
    for dest_id in ranked_dests[:NUM_DEST_ATTEMPTS]:
        dest_code_query = db_manager.query("""
        SELECT city_code FROM destination WHERE id={dest_id}
        """.format(dest_id=dest_id))[0][0]
        flight_options = flights.get_direct_flights_from_origin_to_desintaion(
            get_origin_code(constraints["origin"]), dest_code_query, constraints["departure_date"], constraints["return_date"], constraints["travellers"], constraints["budget_currency"])
        if len(flight_options) == 0:
            num_no_flights += 1
        else:
            accommodation_options = accommodation.get_accommodation_options(dest_code_query, constraints["departure_date"], constraints["return_date"], constraints["travellers"],
                                                                            constraints["accommodation_type"], constraints["accommodation_stars"], constraints["accommodation_amenities"], constraints["budget_currency"])
            if len(accommodation_options) == 0:
                raise NoResults("No accommodation options")
            if destination_satisfies_budget(flight_options[0]["price"], dest_id, constraints, accommodation_options, constraints["budget_leq"]):
                if destination_satisfies_feedback(dest_id, flight_options, accommodation_options, ranked_dests, constraints, feedback):
                    dest_query = db_manager.query("""
                    SELECT name FROM destination WHERE id = {id}
                    """.format(id=dest_id))
                    return dest_id, dest_query[0][0], flight_options, accommodation_options
                else:
                    num_feedback_invalid += 1
            else:
                num_low_budget += 1
    if num_no_flights == max(num_no_flights, num_feedback_invalid, num_low_budget):
        raise NoResults('No flights available on these dates')
    elif num_feedback_invalid == max(num_no_flights, num_feedback_invalid, num_low_budget):
        raise NoResults('Cannot find any destinations for the given feedback')
    elif num_low_budget == max(num_no_flights, num_feedback_invalid, num_low_budget):
        raise NoResults('Budget is too low')
    else:
        raise NoResults('No Results')


def destination_satisfies_feedback(dest_id, flight_options, accommodation_options, ranked_dests, constraints, feedback):
    if feedback == None:
        return True
    if feedback["previous_dest_id"] == dest_id:
        return False
    if feedback["type"] == "cheaper":
        return destination_satisfies_budget(flight_options[0]["price"], dest_id, constraints, accommodation_options, feedback["previous_price"])
    if feedback["type"] == "closer":
        previous_travel_duration = feedback["previous_travel_duration"]
        travel_duration = flight_options[0]["outbound"]["duration"]
        return travel_duration < previous_travel_duration
    if feedback["type"] == "better_weather":
        previous_av_temp = feedback["previous_av_temp"]
        month = datetime.strptime(
            constraints["departure_date"], "%Y-%m-%d").month
        av_temp_c, num_days_rainfall = get_dest_weather(dest_id, month)
        return av_temp_c > previous_av_temp
    if feedback["type"] == "more_activity":
        n = get_preferred_activities_similarity(
            dest_id, [feedback["activity_id"]], 1)
        previous_n = feedback["previous_num"]
        return n > previous_n
    return True


def destination_satisfies_budget(flight_price, dest_id, constraints, accommodation_options, budget):
    currency_conversion = 1
    if flight_price["currency"] != constraints["budget_currency"]:
        currency_conversion = exchange_rates.get_exchange_rate(
            flight_price["currency"], constraints["budget_currency"])
    num_travellers = constraints["travellers"]["adults"] + \
        constraints["travellers"]["children"]
    flight_converted_price = float(flight_price["amount"]) * \
        currency_conversion

    for hotel in accommodation_options:
        hotel_price = hotel["price"]["amount"]
        total_price = flight_converted_price + hotel_price
        if total_price < budget:
            return True
    return False


def get_destination_from_airport(code):
    getDestQuery = db_manager.query("""
    SELECT destination.id, destination.name FROM destination 
    JOIN airports ON airports.municipality = destination.name 
        AND airports.iso_country = destination.country_code
    WHERE airports.iata_code = "{code}"
    """.format(code=code))
    return getDestQuery[0][0], getDestQuery[0][1]


def get_destination_from_city(dest_id, dests):
    if dest_id in dests:
        return dest_id, dests[dest_id]["name"]
    raise NoResults('Cannot fly to this destination')


def dests_from_constraints_recommender(constraints):
    dests = get_flyable_dests(constraints)
    if len(dests) == 0:
        raise NoResults(
            'No flights available on these dates')
    # TODO: Perform constraint based stuff on dests here
    have_dest_query = db_manager.query("""
    SELECT id FROM destination WHERE tourist_score IS NOT NULL
    """)
    all_dest_ids = list(map(lambda d: d[0], have_dest_query))
    valid_dests = {}
    for dest in dests.items():
        if dest[0] in all_dest_ids:
            valid_dests[dest[0]] = dest[1]
    return valid_dests


def get_flyable_dests(constraints):
    origin = get_airport_and_city_code(constraints["origin"])
    departure_date = constraints["departure_date"]
    travellers = constraints["travellers"]

    if (constraints["trip_type"] == "Return"):
        return_date = constraints["return_date"]
        all_flights = flights.get_all_return_flights(
            origin, departure_date, return_date)

    elif (constraints["trip_type"] == "One Way"):
        all_flights = flights.get_all_one_way_flights(
            origin, departure_date)

    return all_flights


def get_airport_and_city_code(dest):
    if dest["type"] == "airport":
        dests_for_airport_codes = db_manager.query("""
        SELECT destination.city_code
        FROM destination
        JOIN airports ON destination.name = airports.municipality AND destination.country_code = airports.iso_country
        WHERE airports.iata_code = "{airport_code}"
        """.format(airport_code=dest["id"]))
        return dests_for_airport_codes[0][0]
    elif dest["type"] == "city":
        city_code_query = db_manager.query("""
        SELECT city_code FROM destination WHERE id = "{id}"
        """.format(id=dest["id"]))
        return city_code_query[0][0]


def prefs_recommender(softPrefs, dests):
    preferred_activities = softPrefs["preferred_activities"]
    similarities = {}
    for dest in dests:
        similarities[dest] = 0
        similarities[dest] += get_preferred_activities_similarity(
            dest, softPrefs["preferred_activities"], 1)

    return similarities


def get_preferred_activities_similarity(dest, preferred_activities, weight):
    if len(preferred_activities) > 0:
        poi_query = db_manager.query("""
        SELECT COUNT(id) FROM poi WHERE destination_id = {dest_id} AND foursquare_category_id IN {cats}
        """.format(dest_id=dest, cats=list_to_tuple(preferred_activities)))
        similarity = poi_query[0][0]
        return weight * similarity
    return 0


def scores_recommender(pref_scores, dest_similarities):
    pref_scores_similarities = {}

    dests_query = db_manager.query("""
    SELECT id, culture_score, learn_score, relax_score FROM destination WHERE id IN {dests} AND culture_score IS NOT NULL
    """.format(dests=list_to_tuple(dest_similarities.keys())))

    for dest_scores in dests_query:
        pref_scores_similarity = abs(
            pref_scores["culture"] - dest_scores[1]) + abs(pref_scores["learn"] - dest_scores[2]) + abs(pref_scores["relax"] - dest_scores[3])
        pref_scores_similarities[dest_scores[0]] = pref_scores_similarity

    return pref_scores_similarities
