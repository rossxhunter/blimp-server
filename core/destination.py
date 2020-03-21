from config import dbManager
import apis.wikipedia as wikipedia
import apis.amadeus as amadeus
import apis.foursquare as foursquare
from flask.json import jsonify


def calculate_destination(constraints, softPrefs, prefScores):
    # calculateDestinationScores()
    dests = performDSConstraintBasedRecommender(constraints)
    # populatePoITable()
    performDSCaseBasedRecommender1(softPrefs)
    performDSCaseBasedRecommender2(prefScores, dests)
    getDestQuery = dbManager.query("""
    SELECT id,name FROM viable_destination ORDER BY score ASC LIMIT 1
    """)
    dest_id = getDestQuery[0][0]
    name = getDestQuery[0][1]
    wiki_entry = wikipedia.getWikiDescription(name)
    return jsonify(name="London", wiki=wikipedia.getWikiDescription("London"), destId=2643743)
    return jsonify(name=name, wiki=wiki_entry, destId=dest_id)


def getFromJSONList(list, field):
    listOfResults = []
    for entry in list:
        if (entry["property"] == field):
            listOfResults.append(str(entry["value"]))
    return listOfResults


def performDSConstraintBasedRecommender(constraints):
    origin = getFromJSONList(constraints, "origin")
    departureDate = getFromJSONList(constraints, "departureDate")
    flights = amadeus.getAllDirectFlights(origin, departureDate)
    dests = getDestsFromFlights(flights)
    destsstr = listToStr(dests)
    return dests


def performDSCaseBasedRecommender1(softPrefs):
    preferred_activities = getFromJSONList(softPrefs, "preferred_activity")
    pref_act_ids = dbManager.query("""
  SELECT id FROM categories WHERE name IN {preferred_activities};
  """.format(preferred_activities=listToTuple(preferred_activities)))

    return


def calculateDestinationScores():
    poi_counts = dbManager.query("""
  SELECT destination_id, category_id, COUNT(id) FROM poi
  GROUP BY category_id, destination_id;
  """)
    scores = {}
    score_totals = {}
    for poi_count in poi_counts:
        if poi_count[0] in scores.keys():
            scores[poi_count[0]].append((poi_count[1], poi_count[2]))
        else:
            scores.update({poi_count[0]: [(poi_count[1], poi_count[2])]})

        if poi_count[0] in score_totals.keys():
            score_totals[poi_count[0]] += poi_count[2]
        else:
            score_totals.update({poi_count[0]: poi_count[2]})

    for dest_id, dest_scores in scores.items():
        feature_scores = {"culture": 0, "learn": 0, "action": 0, "party": 0, "sport": 0,
                          "food": 0, "relax": 0, "nature": 0, "shopping": 0, "romantic": 0, "family": 0}
        for dest_cat_score in dest_scores:
            poi_scores = dbManager.query("""
            SELECT culture_score, learn_score, action_score, party_score, sport_score, food_score, relax_score, nature_score, shopping_score, romantic_score, family_score FROM categories WHERE id = \"{cat_id}\";
            """ .format(cat_id=dest_cat_score[0]))[0]
            feature_scores["culture"] += dest_cat_score[1] * poi_scores[0]
            feature_scores["learn"] += dest_cat_score[1] * poi_scores[1]
            feature_scores["action"] += dest_cat_score[1] * poi_scores[2]
            feature_scores["party"] += dest_cat_score[1] * poi_scores[3]
            feature_scores["sport"] += dest_cat_score[1] * poi_scores[4]
            feature_scores["food"] += dest_cat_score[1] * poi_scores[5]
            feature_scores["relax"] += dest_cat_score[1] * poi_scores[6]
            feature_scores["nature"] += dest_cat_score[1] * poi_scores[7]
            feature_scores["shopping"] += dest_cat_score[1] * poi_scores[8]
            feature_scores["romantic"] += dest_cat_score[1] * poi_scores[9]
            feature_scores["family"] += dest_cat_score[1] * poi_scores[10]
        for feature, score in feature_scores.items():
            feature_scores[feature] = getSimplifiedScore(score)
        poi_counts = dbManager.insert("""
        UPDATE destination SET culture_score={culture_score}, learn_score={learn_score}, action_score={action_score}, party_score={party_score}, sport_score={sport_score}, food_score={food_score}, relax_score={relax_score}, nature_score={nature_score}, shopping_score={shopping_score}, romantic_score={romantic_score}, family_score={family_score} WHERE id={dest_id};
        """ .format(culture_score=feature_scores["culture"], learn_score=feature_scores["learn"], action_score=feature_scores["action"], party_score=feature_scores["party"], sport_score=feature_scores["sport"], food_score=feature_scores["food"], relax_score=feature_scores["relax"], nature_score=feature_scores["nature"], shopping_score=feature_scores["shopping"], romantic_score=feature_scores["romantic"], family_score=feature_scores["family"], dest_id=dest_id))


def getSimplifiedScore(score):
    return 5 if score > 100 else score // 20


def populatePoITable():
    dests = dbManager.query("""
  SELECT id, latitude, longitude FROM viable_destination
  """)
    arts_entertainment = "4d4b7104d754a06370d81259"
    event = "4d4b7105d754a06373d81259"
    nightlife_spot = "4d4b7105d754a06376d81259"
    outdoors_recreation = "4d4b7105d754a06377d81259"
    professional_other = "4d4b7105d754a06375d81259"
    cats = arts_entertainment + "," + event + "," + nightlife_spot + \
        "," + outdoors_recreation + "," + professional_other
    poisForDB = []
    for dest in dests:

        pois = foursquare.getNearbyPOIs(
            str(dest[1]), str(dest[2]), cats)["response"]
        if "groups" in pois:
            pois = pois["groups"][0]["items"]
            for poi in pois:
                poi = poi["venue"]
                poiForDB = {"id": poi["id"], "name": poi["name"],
                            "latitude": poi["location"]["lat"], "longitude": poi["location"]["lng"], "category_id": poi["categories"][0]["id"], "destination_id": dest[0]}
                dbManager.insert("""
                REPLACE INTO poi (id, name, latitude, longitude, category_id, destination_id)
                VALUES (\"{id}\", \"{name}\", {latitude}, {longitude}, \"{category_id}\", {destination_id});
                """.format(id=poiForDB["id"], name=poiForDB["name"].replace('"', '\\"'),  latitude=poiForDB["latitude"], longitude=poiForDB["longitude"], category_id=poiForDB["category_id"], destination_id=poiForDB["destination_id"]))
            print("DONE!")


def listToTuple(list):
    t = "("
    for i in list:
        t += "'" + str(i) + "'" + ","
    if t.endswith(","):
        t = t[:-1]
    return t + ")"


def performDSCaseBasedRecommender2(prefScore, dests):
    getAllViableDestsQuery = """
  CREATE OR REPLACE VIEW viable_destination AS
  SELECT id, name, latitude, longitude, ABS(culture_score - {culture_score}) + ABS(learn_score - {learn_score}) AS score from destination WHERE id IN {dests}
  """ .format(culture_score=prefScore["culture"], learn_score=prefScore["learn"], dests=listToTuple(dests))
    dbManager.query(getAllViableDestsQuery)


def listToStr(list):
    result = "("
    for i in range(0, len(list)):
        result += str(list[i])
        if (i != len(list) - 1):
            result += ","
    result += ")"
    return result


def getDestsFromFlights(flights):
    dests = []
    for i in range(0, len(flights)):
        dests.append(flights[i]["id"])
    return dests
