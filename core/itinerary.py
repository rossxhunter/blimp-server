import apis.mapbox as mapbox
from flask.json import jsonify
from config import dbManager
from datetime import datetime, timedelta
import cProfile
from util.util import divide_round_up, merge_dicts


def calculate_itinerary(destination):
    # cProfile.run('get_POIs_for_destination(destination)')
    pois = get_POIs_for_destination(destination)
    edges = get_durations(pois)
    # edges = create_edges(pois, travel_durations)
    B = 8 * 60 * 60
    T = 30
    k = 2
    # startTime = datetime(year=2020, month=2, day=28, hour=8)
    start_node = ("4ac51183f964a52049a020e3", pois["4ac51183f964a52049a020e3"])
    P, times = multi_tour(
        pois, edges, B, k, start_node, T)
    visitDurations = [1*60*60] * len(pois)
    itinerary = {}
    for i in range(0, len(P)):
        day_itinerary = []
        for j in range(0, len(P[i])):
            day_itinerary.append(
                {"name": P[i][j][1]["name"], "startTime": times[i][j], "duration": visitDurations[0]})
        itinerary[i] = day_itinerary
    return jsonify(itinerary=itinerary)


def multi_tour(pois, edges, budget, num_days, start_node, target_value):
    visitDurations = [1*60*60] * len(pois)
    P_star = []
    t = []
    for poi in pois.items():
        if Utility([poi]) > target_value:
            P, t_P = ([start_node, poi], [0, get_specific_edge(edges, start_node["id"],
                                                               poi[0])])
            P_star.append(P)
            t.append(t_P)
            pois.remove(poi)
    q = len(P_star)
    if q > num_days:
        return (P_star, t)
    for i in range(0, (num_days-q)):
        P, t_P = single_tour(pois, edges, budget, start_node)
        P, t_P = truncate_tour(P, t_P, target_value)
        P_star.append(P)
        t.append(t_P)
        for p in P:
            del pois[p[0]]
    for p in P_star:
        if Utility(p) < 0:
            return ([], [])
    return (P_star, t)


def truncate_tour(P, t_P, target_value):
    for i in range(0, len(P)):
        del P[i]
        del t_P[i]
        total_utility = 0
        for j in range(0, len(P)):
            total_utility += Utility([P[j]])
        if total_utility <= 2 * target_value:
            break
    return (P, t_P)


def single_tour(pois, edges, budget, start_node):
    P_star = [start_node]
    P = []
    while True:
        P = P_star
        best_margin = -1
        P_star = None
        for poi in pois.items():
            if poi not in P:
                P2 = list(P)
                P2.append(poi)
                P2 = TSP(list(P2), edges)
                margin = (Utility(P2) - Utility(P)) / \
                    (Cost(P2, edges) - Cost(P, edges))
                if margin > best_margin and Cost(P2, edges) < budget:
                    best_margin = margin
                    P_star = list(P2)
        if (P_star == None):
            break

    visitDurations = [1*60*60] * len(P)

    times = [0]
    for p in range(0, len(P) - 1):
        if p == 0:
            times.append(times[p] + get_specific_edge(edges, P[p][0],
                                                      P[p + 1][0]))
        else:
            times.append(times[p] + get_specific_edge(edges, P[p][0],
                                                      P[p + 1][0]) + visitDurations[p])
    return (P, times)


def get_durations(pois):
    durations = {}
    missing = {}
    poi_ids = pois.keys()
    poi_ids_string = ", ".join('"{0}"'.format(p) for p in poi_ids)
    get_durations_query = dbManager.query("""
    SELECT start_id, end_id, driving_time FROM travel_time WHERE start_id IN ({start_ids}) AND end_id IN ({end_ids})
    ORDER BY start_id, end_id
    """ .format(start_ids=poi_ids_string, end_ids=poi_ids_string))
    for p1 in pois.items():
        for p2 in pois.items():
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
                                                               MAX_DEST_POIS:(j+1)*MAX_DEST_POIS]
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
            insert_durations = dbManager.insert("""
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


def Cost(path, edges):
    timeAtPOIs = (len(path) - 1) * 1 * 60 * 60
    travellingTime = 0
    for p in range(0, len(path) - 1):
        duration = get_specific_edge(edges, path[p][0],
                                     path[p + 1][0])
        travellingTime += duration
    return timeAtPOIs + travellingTime


def Utility(path):
    total = 0
    for p in path:
        total += p[1]["score"]
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


def get_POIs_for_destination(destination):
    getPOIsQuery = dbManager.query("""
    SELECT poi.id,poi.name,poi.latitude,poi.longitude,categories.culture_score,categories.learn_score,categories.relax_score FROM poi
    INNER JOIN categories ON poi.category_id = categories.id 
    WHERE poi.destination_id={destination}
    ORDER BY poi.id
    LIMIT 50
    """ .format(destination=destination))
    pois = {}
    for poi in getPOIsQuery:
        score = poi[4] + poi[5] + poi[6]
        pois[poi[0]] = {"name": poi[1],
                        "latitude": poi[2], "longitude": poi[3], "score": score}
    return pois
