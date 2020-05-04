import apis.mapbox as mapbox
from flask.json import jsonify
from config import db_manager
from datetime import datetime, timedelta
from util.util import divide_round_up, merge_dicts
import apis.amadeus as amadeus
from util.exceptions import NoResults


def calculate_itinerary_for_evaluation(dest_id, num_days, constraints, soft_prefs, pref_scores):
    pois = get_POIs_for_destination(dest_id, pref_scores)
    start_location = db_manager.query("""
    SELECT latitude, longitude FROM destination WHERE id = {dest_id}
    """.format(dest_id=dest_id))[0]
    start_node = ("start", {
        "latitude": start_location[0], "longitude": start_location[1], "score": 0, "popularity": 0, "rating": 0})
    edges = get_durations(pois, start_node)
    T = 30000000
    budgets = [8 * 60 * 60] * num_days
    start_times = [8 * 60 * 60] * num_days
    preferred_activities = soft_prefs["preferred_activities"]
    essential_activities = constraints["essential_activities"]
    P, times = multi_tour(
        pois, edges, budgets, start_times, num_days, start_node, T, None, preferred_activities, essential_activities)
    visitDuration = 2*60*60
    itinerary = {}
    for i in range(0, len(P)):
        day_itinerary = []
        for j in range(0, len(P[i])):
            day_itinerary.append(
                {"id": P[i][j][0], "name": P[i][j][1]["name"], "description": P[i][j][1]["description"], "latitude": P[i][j][1]["latitude"], "longitude": P[i][j][1]["longitude"], "score": P[i][j][1]["score"], "rating": P[i][j][1]["rating"], "popularity": P[i][j][1]["popularity"], "bestPhoto": P[i][j][1]["bestPhoto"], "category": P[i][j][1]["category"], "startTime": times[i][j], "duration": visitDuration})
        itinerary[i] = day_itinerary
    return itinerary


def calculate_itinerary(pois, travel, accommodation, constraints, soft_prefs, pref_scores, poi_order=None, day=None):
    start_node = ("start", {
        "latitude": accommodation["latitude"], "longitude": accommodation["longitude"], "score": 0, "popularity": 0, "rating": 0})

    edges = get_durations(pois, start_node)

    T = 3000000000

    budgets, start_times = get_daily_time_budgets_and_start_times(travel)

    if poi_order == None:
        k = len(budgets)
        visit_duration = [[2*60*60] * 10] * k
    else:
        k = 1
        budgets = [budgets[day]]
        start_times = [start_times[day]]
        visit_duration = [list(map(lambda p: p["duration"], poi_order))]

    preferred_activities = soft_prefs["preferred_activities"]
    essential_activities = constraints["essential_activities"]
    P, times = multi_tour(
        pois, edges, budgets, start_times, k, start_node, T, poi_order, preferred_activities, essential_activities)

    itinerary = {}
    for i in range(0, len(P)):
        day_itinerary = []
        for j in range(0, len(P[i])):
            day_itinerary.append(
                {"id": P[i][j][0], "name": P[i][j][1]["name"], "description": P[i][j][1]["description"], "latitude": P[i][j][1]["latitude"], "longitude": P[i][j][1]["longitude"], "score": P[i][j][1]["score"], "rating": P[i][j][1]["rating"], "popularity": P[i][j][1]["popularity"], "bestPhoto": P[i][j][1]["bestPhoto"], "category": P[i][j][1]["category"], "categoryId": P[i][j][1]["categoryId"], "startTime": times[i][j], "duration": visit_duration[i][j]})
        itinerary[i] = day_itinerary
    return itinerary


def get_daily_time_budgets_and_start_times(travel):
    budgets = []
    start_times = []
    time_from_airport_to_hotel = 1.5 * 60 * 60
    time_from_hotel_to_airport = 3 * 60 * 60
    standard_budget = 8 * 60 * 60
    arrival_date = datetime.strptime(
        travel["outbound"]["departure"]["date"], "%Y%m%d")
    departure_date = datetime.strptime(
        travel["return"]["departure"]["date"], "%Y%m%d")
    stay_duration = departure_date.day - arrival_date.day + 1
    start_time = 8 * 60 * 60
    end_time = 16 * 60 * 60
    for i in range(0, stay_duration):
        if i == 0:
            arrival_time = datetime.strptime(
                travel["outbound"]["arrival"]["time"], "%H:%M")
            arrival_seconds = (arrival_time.hour * 60 * 60) + \
                (arrival_time.minute * 60) + time_from_airport_to_hotel
            b = end_time - arrival_seconds
            start_times.append(arrival_seconds)
        elif i == stay_duration - 1:
            departure_time = datetime.strptime(
                travel["return"]["departure"]["time"], "%H:%M")
            departure_seconds = (departure_time.hour * 60 *
                                 60) + (departure_time.minute * 60) - time_from_hotel_to_airport
            b = departure_seconds - start_time
            start_times.append(start_time)
        else:
            b = standard_budget
            start_times.append(start_time)
        if b > 0:
            budgets.append(min(b, standard_budget))
        else:
            budgets.append(0)
    return budgets, start_times


def multi_tour(pois, edges, budgets, start_times, num_days, start_node, target_value, poi_order, preferred_activities, essential_activities):
    P_star = []
    t = []
    # for poi in pois.items():
    #     if Utility([poi], preferred_activities, essential_activities) > target_value:
    #         P, t_P = ([start_node, poi], [0, get_specific_edge(edges, start_node[0],
    #                                                            poi[0])])
    #         P_star.append(P)
    #         t.append(t_P)
    #         pois.remove(poi)
    q = len(P_star)
    if q > num_days:
        return (P_star, t)
    for i in range(0, (num_days-q)):
        P, t_P = single_tour(
            pois, edges, budgets[i], start_times[i], start_node, poi_order, preferred_activities, essential_activities)
        P, t_P = truncate_tour(P, t_P, target_value,
                               preferred_activities, essential_activities)
        P_star.append(P)
        t.append(t_P)
        for p in P:
            del pois[p[0]]
    for p in P_star:
        if Utility(p, preferred_activities, essential_activities) < 0:
            return ([], [])
        for poi in p:
            if poi[1]["categoryId"] in essential_activities:
                essential_activities.remove(poi[1]["categoryId"])

    if len(essential_activities) > 0:
        raise NoResults("Cannot include all essential activties")

    return (P_star, t)


def truncate_tour(P, t_P, target_value, preferred_activities, essential_activities):
    for p in P:
        del P[0]
        del t_P[0]
        total_utility = 0
        for j in range(0, len(P)):
            total_utility += Utility([P[j]],
                                     preferred_activities, essential_activities)
        if total_utility <= 2 * target_value:
            break
    return (P, t_P)


def single_tour(pois, edges, budget, start_time, start_node, poi_order, preferred_activities, essential_activities):
    P_star = [start_node]
    P = []
    visit_durations = None
    if poi_order != None:
        expected_num_pois = len(poi_order)
        visit_durations = list(map(lambda p: p["duration"], poi_order))

    while True:
        P = P_star
        best_margin = -1
        P_star = None
        poi_found = False
        for poi in pois.items():
            if poi not in P and not poi_found:
                P2 = list(P)
                P2.append(poi)
                P2 = TSP(list(P2), edges)
                margin = (Utility(P2, preferred_activities, essential_activities) - Utility(P, preferred_activities, essential_activities)) / \
                    (Cost(P2, edges, visit_durations) -
                     Cost(P, edges, visit_durations))
                if poi_order != None and poi[0] == poi_order[0]["id"] and Cost(P2, edges, visit_durations) < budget:
                    poi_order.pop(0)
                    poi_found = True
                    best_margin = margin
                    P_star = list(P2)
                elif margin > best_margin and Cost(P2, edges, visit_durations) < budget:
                    best_margin = margin
                    P_star = list(P2)

        if (P_star == None):
            break
        elif P_star[-1][1]["categoryId"] in essential_activities:
            essential_activities.remove(P_star[-1][1]["categoryId"])

    if (poi_order != None and len(P) <= expected_num_pois):
        raise NoResults(
            "Cannot fit all the activities within time window. Try removing an activity or increasing the time window.")
    if visit_durations == None:
        visit_durations = [2*60*60] * len(P)

    times = [start_time]
    for p in range(0, len(P) - 1):
        if p == 0:
            times.append(times[p] + get_specific_edge(edges, P[p][0],
                                                      P[p + 1][0]))
        else:
            times.append(times[p] + get_specific_edge(edges, P[p][0],
                                                      P[p + 1][0]) + visit_durations[p - 1])
    return (P, times)


def get_durations(pois, start_node):
    all_pois = dict(pois)
    all_pois[start_node[0]] = start_node[1]
    durations = {}
    missing = {}
    poi_ids = all_pois.keys()
    poi_ids_string = ", ".join('"{0}"'.format(p) for p in poi_ids)
    get_durations_query = db_manager.query("""
    SELECT start_id, end_id, driving_time FROM travel_time WHERE start_id IN ({start_ids}) AND end_id IN ({end_ids})
    ORDER BY start_id, end_id
    """ .format(start_ids=poi_ids_string, end_ids=poi_ids_string))
    for p1 in all_pois.items():
        for p2 in all_pois.items():
            missing[(p1[0], p2[0])] = (p1[1], p2[1])
    for d in get_durations_query:
        durations[(d[0], d[1])] = d[2]
        del missing[(d[0], d[1])]

    if (len(missing) > 0):
        new_durations = get_missing_durations(missing.items())
        durations = merge_dicts(durations, new_durations)

    return durations


def get_missing_sources_and_dests(missing):
    missing_sources = {}
    missing_dests = {}
    for pair in missing:
        if pair[0][0] not in missing_dests.keys() or pair[0][1] not in missing_sources.keys():
            if pair[0][0] not in missing_sources.keys():
                missing_sources[pair[0][0]] = pair[1][0]
            if pair[0][1] not in missing_dests.keys():
                missing_dests[pair[0][1]] = pair[1][1]
    return missing_sources, missing_dests


def get_missing_durations(missing):
    durations = {}
    missing_sources, missing_dests = get_missing_sources_and_dests(missing)
    MAX_POIS_FOR_MAPBOX_MATRIX = 25
    MAX_SOURCE_POIS = 12
    num_iterations_sources = divide_round_up(
        len(missing_sources), MAX_SOURCE_POIS)
    for i in range(0, num_iterations_sources):
        missing_sources_subset = list(missing_sources.items())[i*MAX_SOURCE_POIS:(
            i+1)*MAX_SOURCE_POIS]
        MAX_DEST_POIS = MAX_POIS_FOR_MAPBOX_MATRIX - MAX_SOURCE_POIS
        num_iterations_dests = divide_round_up(
            len(missing_dests), MAX_DEST_POIS)
        for j in range(0, num_iterations_dests):
            missing_dests_subset = list(missing_dests.items())[j *
                                                               MAX_DEST_POIS: (j+1)*MAX_DEST_POIS]
            missing_matrix = missing_sources_subset + missing_dests_subset
            missing_coords = []
            for poi in missing_matrix:
                missing_coords.append(
                    [poi[1]["longitude"], poi[1]["latitude"]])
            new_durations_1 = get_mapbox_durations(
                missing_coords, missing_sources_subset, missing_dests_subset, False)
            missing_coords_rev = list(missing_coords)
            missing_coords_rev.reverse()
            new_durations_2 = get_mapbox_durations(
                missing_coords_rev, missing_dests_subset, missing_sources_subset, True)
            new_durations = merge_dicts(new_durations_1, new_durations_2)
            new_durations_insert = get_new_durations_insert(new_durations)
            if (len(new_durations_insert) != 0):
                insert_durations = db_manager.insert("""
                REPLACE INTO travel_time (start_id, end_id, driving_time) VALUES {new_durations}
                """ .format(new_durations=new_durations_insert))
            durations = merge_dicts(durations, new_durations)
    return durations


def get_mapbox_durations(missing_coords, missing_subset_1, missing_subset_2, is_flipped):
    mapbox_durations = mapbox.getMatrix(missing_coords, "driving", sources=list(range(0, len(
        missing_subset_1))), destinations=list(range(len(missing_subset_1), len(missing_coords)))).json()["durations"]
    new_durations = {}
    for i in range(0, len(mapbox_durations)):
        for j in range(0, len(mapbox_durations[0])):
            a = i
            b = j
            if is_flipped:
                a = len(mapbox_durations) - i - 1
                b = len(mapbox_durations[i]) - j - 1
            new_durations[(missing_subset_1[a][0],
                           missing_subset_2[b][0])] = mapbox_durations[i][j]
    return new_durations


def get_new_durations_insert(durations):
    s = ""
    for d in durations.items():
        if (d[0][0] != "start" and d[0][1] != "start"):
            s += "(\"" + str(d[0][0]) + "\",\"" + \
                str(d[0][1]) + "\"," + str(d[1]) + ")" + ","
    if s.endswith(","):
        s = s[:-1]
    return s


def get_travel_time(l, start, end):
    for t in l:
        if (t[0] == start and t[1] == end):
            return t
    return None


def get_specific_edge(edges, startId, endId):
    return edges[(startId, endId)]


def Cost(path, edges, visit_durations):
    totalTime = 0
    for p in range(0, len(path) - 1):
        travellingTime = get_specific_edge(edges, path[p][0],
                                           path[p + 1][0])
        if visit_durations == None:
            visit_duration = 2 * 60 * 60
        else:
            visit_duration = visit_durations[p]

        totalTime += travellingTime + visit_duration
    return totalTime


def Utility(path, preferred_activities, essential_activities):
    total = 0
    for p in path:
        if p[0] != "start":
            additional_total = p[1]["score"] + \
                p[1]["popularity"] * p[1]["rating"]
            if p[1]["categoryId"] in essential_activities:
                additional_total *= 10000000
            elif p[1]["categoryId"] in preferred_activities:
                additional_total *= 2
            total += additional_total
    return total


def TSP(pois, edges):
    result = list([pois[0]])
    del pois[0]
    while len(pois) > 0:
        relevantEdges = []
        shortestEdgeEnd = pois[0][0]
        for poi in pois:
            relevantEdges.append(get_specific_edge(
                edges, result[-1][0], poi[0]))
        shortestEdge = relevantEdges[0]
        del relevantEdges[0]
        for relevantEdge in relevantEdges:
            if relevantEdge < shortestEdge:
                shortestEdge = relevantEdge
        for i in range(0, len(pois)):
            if (pois[i][0] == shortestEdgeEnd):
                result.append(pois[i])
                del pois[i]
                break
    return result


def get_POIs_for_destination(destination, pref_scores):
    getPOIsQuery = db_manager.query("""
    SELECT poi.id,poi.name,poi.latitude,poi.longitude,poi.num_ratings,poi.rating,poi.wiki_description,poi_photo.url,categories.id,categories.name,categories.icon_prefix,categories.culture_score,categories.learn_score,categories.relax_score FROM poi
    JOIN poi_photo ON poi_photo.poi_id = poi.id
    JOIN categories ON poi.foursquare_category_id = categories.id
    WHERE poi.destination_id={destination}
    ORDER BY poi.num_ratings DESC
    LIMIT 60
    """ .format(destination=destination))
    pois = {}
    for poi in getPOIsQuery:
        score = 1
        poi_scores = {"culture": poi[11] or 3,
                      "learn": poi[12] or 3, "relax": poi[13] or 3}
        for pref in pref_scores.keys():
            score += 5 - abs(pref_scores[pref] - poi_scores[pref])
        pois[poi[0]] = {"name": poi[1],
                        "latitude": poi[2], "longitude": poi[3], "score": score, "popularity": poi[4] if poi[4] != None else 0, "rating": poi[5] if poi[5] != None else 0, "description": poi[6], "bestPhoto": poi[7], "categoryId": poi[8], "category": poi[9], "categoryIcon": poi[10]}
    return pois
