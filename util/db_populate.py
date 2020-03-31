from config import db_manager
from apis import foursquare
from apis import wikipedia


def populate_POI_details():
    dest_id = db_manager.query("""
    SELECT id FROM viable_destination WHERE name="London"
    """)[0][0]
    pois = db_manager.query("""
    SELECT id FROM poi WHERE destination_id="{dest_id} AND tip_count IS NULL"
    """.format(dest_id=dest_id))
    for poi in pois:
        poi = poi[0]
        details = foursquare.get_POI_details(poi)
        print(details)
        venue = details["response"]["venue"]
        detailsInsert = db_manager.insert("""
        UPDATE poi SET tip_count = {tip_count}, rating = {rating}, description = "{description}", best_photo = "{best_photo}"
        WHERE id = "{poi_id}"
        """.format(tip_count=venue["stats"]["tipCount"], rating=venue["rating"] if "rating" in venue else 0, description=venue["description"] if "description" in venue else "", best_photo=venue["bestPhoto"]["prefix"] + "800" + venue["bestPhoto"]["suffix"], poi_id=poi))


def populate_POI_table():
    dests = db_manager.query("""
  SELECT id, latitude, longitude FROM viable_destination WHERE name="Florence"
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

        pois = foursquare.get_nearby_POIs(
            str(dest[1]), str(dest[2]), cats)["response"]
        if "groups" in pois:
            pois = pois["groups"][0]["items"]
            for poi in pois:
                poi = poi["venue"]
                poiForDB = {"id": poi["id"], "name": poi["name"],
                            "latitude": poi["location"]["lat"], "longitude": poi["location"]["lng"], "category_id": poi["categories"][0]["id"], "destination_id": dest[0]}
                db_manager.insert("""
                REPLACE INTO poi (id, name, latitude, longitude, category_id, destination_id)
                VALUES (\"{id}\", \"{name}\", {latitude}, {longitude}, \"{category_id}\", {destination_id});
                """.format(id=poiForDB["id"], name=poiForDB["name"].replace('"', '\\"'),  latitude=poiForDB["latitude"], longitude=poiForDB["longitude"], category_id=poiForDB["category_id"], destination_id=poiForDB["destination_id"]))
            print("DONE!")


def add_codes():
    codes_query = db_manager.query("""
    SELECT id,name FROM city_code;
    """)
    for code in codes_query:
        ins = db_manager.insert("""
        UPDATE destination SET city_code = \"{city_code}\" WHERE name = \"{city_name}\"                       
        """.format(city_code=code[0], city_name=code[1]))


def populate_destination_images():
    destsQuery = db_manager.query("""
    SELECT id,name FROM destination ORDER BY population DESC LIMIT 10
    """)
    for dest_id, dest_name in destsQuery:
        image = wikipedia.get_wiki_image(dest_name)
        destImageInsert = db_manager.insert("""
        UPDATE destination SET image_url = "{image_url}" WHERE id = {dest_id}
        """.format(image_url=image, dest_id=dest_id))


def calculate_destination_scores():
    poi_counts = db_manager.query("""
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
            poi_scores = db_manager.query("""
            SELECT culture_score, learn_score, action_score, party_score, sport_score, food_score, relax_score, nature_score, shopping_score, romantic_score, family_score FROM categories WHERE id = "{cat_id}";
            """.format(cat_id=dest_cat_score[0]))[0]
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
            feature_scores[feature] = get_simplified_score(
                score, score_totals[dest_id])
        poi_counts = db_manager.insert("""
        UPDATE destination SET culture_score={culture_score}, learn_score={learn_score}, action_score={action_score}, party_score={party_score}, sport_score={sport_score}, food_score={food_score}, relax_score={relax_score}, nature_score={nature_score}, shopping_score={shopping_score}, romantic_score={romantic_score}, family_score={family_score} WHERE id={dest_id};
        """ .format(culture_score=feature_scores["culture"], learn_score=feature_scores["learn"], action_score=feature_scores["action"], party_score=feature_scores["party"], sport_score=feature_scores["sport"], food_score=feature_scores["food"], relax_score=feature_scores["relax"], nature_score=feature_scores["nature"], shopping_score=feature_scores["shopping"], romantic_score=feature_scores["romantic"], family_score=feature_scores["family"], dest_id=dest_id))


def get_simplified_score(score, total):
    normalised_score = score / total
    if normalised_score == 0:
        return 0
    elif normalised_score > 1:
        return 5
    else:
        return round(normalised_score / 0.2)
