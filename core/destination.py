from config import db_manager
from apis import wikipedia, exchange_rates
from flask.json import jsonify
from util.util import list_to_tuple, listToStr, get_list_of_values_from_list_of_dicts, get_origin_code
from util.db_populate import populate_POI_details, populate_POI_table, add_codes, populate_destination_images
from util.exceptions import NoResults
from core import accommodation, flights


def calculate_destination(constraints, soft_prefs, pref_scores):
    dests = dests_from_constraints_recommender(constraints)
    if ("destination" in constraints):
        if (constraints["destination"]["type"] == "city"):
            dest_id, name = get_destination_from_city(
                constraints["destination"]["id"])

        elif (constraints["destination"]["type"] == "airport"):
            dest_id, name = get_destination_from_airport(
                constraints["destination"]["id"])

        ranked_dests = [dest_id]

    else:
        dest_ids = dests.keys()
        dests_soft_prefs_similarities = prefs_recommender(soft_prefs, dest_ids)
        dests_pref_scores_similarities = scores_recommender(
            pref_scores, dests_soft_prefs_similarities)
        add_to_viable_dests(
            dest_ids, dests_soft_prefs_similarities, dests_pref_scores_similarities)
        ranked_dests = get_ranked_dests(
            dests_soft_prefs_similarities, dests_pref_scores_similarities)

    dest_id, name, flight_options, accommodation_options = select_dest_from_ranked_dests(
        dests, ranked_dests, constraints)

    wiki_entry = wikipedia.getWikiDescription(name)

    return {"name": name, "wiki": wiki_entry, "id": dest_id, "flights": flight_options, "accommodation": accommodation_options}


def get_ranked_dests(dests_soft_prefs_similarities, dests_pref_scores_similarities):
    return sorted(dests_soft_prefs_similarities,
                  key=dests_soft_prefs_similarities.get, reverse=True)


def add_to_viable_dests(dests, dests_soft_prefs_similarities, dests_pref_scores_similarities):
    for dest in dests:
        viable_insert = db_manager.insert("""
        REPLACE INTO viable_destinations (id, name, soft_prefs_sim, pref_scores_sim) VALUES ({id}, (SELECT name FROM destination WHERE id = {id}), {soft_prefs_sim}, {pref_scores_sim})
        """.format(id=dest, soft_prefs_sim=dests_soft_prefs_similarities[dest], pref_scores_sim=dests_pref_scores_similarities[dest]))


def select_dest_from_ranked_dests(dests, ranked_dests, constraints):
    num_no_flights = 0
    for dest_id in ranked_dests[:3]:
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
            if destination_satisfies_budget(flight_options[0]["price"], dest_id, constraints, accommodation_options):
                dest_query = db_manager.query("""
                SELECT name FROM destination WHERE id = {id}
                """.format(id=dest_id))
                return dest_id, dest_query[0][0], flight_options, accommodation_options
    if num_no_flights == 3:
        raise NoResults(
            'No flights available on these dates')
    else:
        raise NoResults(
            'Budget is too low')


def destination_satisfies_budget(flight_price, dest_id, constraints, accommodation_options):
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
        if total_price <= constraints["budget_leq"]:
            return True
    return False


def get_destination_from_airport(code):
    getDestQuery = db_manager.query("""
            SELECT id,name FROM viable_destinations WHERE name IN 
            (SELECT municipality FROM airports WHERE iata_code="{code}")
            """.format(code=code))
    if (len(getDestQuery) == 0):
        raise NoResults(
            'Cannot fly to this airport')
    return getDestQuery[0][0], getDestQuery[0][1]


def get_destination_from_city(id):
    getDestQuery = db_manager.query("""
            SELECT id,name FROM viable_destinations WHERE id = "{id}"
            """.format(id=id))
    if (len(getDestQuery) == 0):
        raise NoResults(
            'Cannot fly to this destination')
    return getDestQuery[0][0], getDestQuery[0][1]


def dests_from_constraints_recommender(constraints):
    dests = get_flyable_dests(constraints)
    if len(dests) == 0:
        raise NoResults(
            'No flights available on these dates')
    # TODO: Perform constraint based stuff on dests here
    return dests


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
            SELECT COUNT(id) FROM poi WHERE destination_id = {dest_id} AND category_id IN {cats}
            """.format(dest_id=dest, cats=list_to_tuple(preferred_activities)))
        similarity = poi_query[0][0]
        return weight * similarity
    return 0


def scores_recommender(pref_scores, dest_similarities):
    pref_scores_similarities = {}

    dests_query = db_manager.query("""
    SELECT id, culture_score, learn_score, relax_score FROM destination WHERE id IN {dests}
    """.format(dests=list_to_tuple(dest_similarities.keys())))

    for dest_scores in dests_query:
        pref_scores_similarity = abs(
            pref_scores["culture"] - dest_scores[1]) + abs(pref_scores["learn"] - dest_scores[2]) + abs(pref_scores["relax"] - dest_scores[3])
        pref_scores_similarities[dest_scores[0]] = pref_scores_similarity

    return pref_scores_similarities
