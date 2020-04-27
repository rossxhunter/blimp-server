from config import db_manager
from apis import foursquare, wikipedia, google_places, pixabay, facebook_places
from core import activities
import urllib
import shutil
import os


def populate_DB():
    # add_codes()
    # populate_POI_table()
    # calculate_tourist_scores()
    # populate_POI_wiki_desc()
    # fetch_POI_image_urls()
    # populate_foursquare_POI_details()
    # populate_facebook_POI_details()
    # calculate_destination_scores()
    # populate_destination_images()
    return


def populate_facebook_POI_details():
    pois = db_manager.query("""
    SELECT id, name, latitude, longitude FROM poi WHERE destination_id = 1796236 AND id = "ChIJ29SwJftwsjURZYXg4jufPhY"
    """)
    for poi in pois:
        fb = facebook_places.search_facebook_place(poi[1], poi[2], poi[3])
        if fb != None:
            facebook_insert = db_manager.insert("""
            UPDATE poi SET facebook_category = "{facebook_category}"
            WHERE id = "{poi_id}"
            """.format(poi_id=poi[0], facebook_category=fb["category_list"][-1]["name"]))


def populate_foursquare_POI_details():
    pois = db_manager.query("""
    SELECT poi.id, poi.name, poi.latitude, poi.longitude, destination.name, destination.country_code 
    FROM poi 
    JOIN destination ON poi.destination_id = destination.id
    WHERE foursquare_category_id IS NULL AND tourist_score IS NOT NULL
    """)
    for poi in pois:
        matches = foursquare.get_POI_match(
            poi[1], poi[2], poi[3], poi[4] + "," + poi[5])
        if len(matches) > 0:
            details = matches[0]
            for match in matches:
                if "flags" in match and "exactMatch" in match["flags"]:
                    details = match
            foursquare_insert = db_manager.insert("""
            UPDATE poi SET foursquare_category_id = "{category_id}", cat_name = "{cat_name}"
            WHERE id = "{poi_id}"
            """.format(poi_id=poi[0], category_id=details["categories"][0]["id"] if len(details["categories"]) != 0 else "4d4b7105d754a06375d81259", cat_name=details["categories"][0]["name"] if len(details["categories"]) != 0 else ""))


def populate_POI_table_from_google_details():
    pois = db_manager.query("""
    SELECT id FROM poi WHERE destination_id = 1796236
    """)
    for poi in pois:
        poi_details = google_places.get_poi_details(poi[0])
        db_manager.insert("""
        UPDATE poi SET name = "{name}", latitude = {latitude}, longitude = {longitude}, rating = {rating}, num_ratings = {num_ratings}, types = "{types}"
        WHERE id = {id}
        """.format(id=poi[0], name=poi_details["name"], latitude=poi_details["geometry"]["location"]["lat"], longitude=poi_details["geometry"]["location"]["lng"], rating=poi_details["rating"] if "rating" in poi else "NULL", num_ratings=poi_details["user_ratings_total"], types=str(poi_details["types"]).replace('"', '').replace("'", "")))
        for photo in poi_details["photos"]:
            db_manager.insert("""
            INSERT INTO poi_photo (reference, poi_id)
            VALUES ({reference}, {poi_id})
            """.format(reference=photo["reference"], poi_id=poi[0]))


def fetch_POI_image_urls():
    refs = db_manager.query("""
    SELECT reference FROM poi_photo WHERE url IS NULL
    """)
    for ref in refs:
        url = google_places.fetch_image_url(ref[0])
        db_manager.insert("""
        UPDATE poi_photo SET url = "{url}"
        WHERE reference = "{reference}"
        """.format(url=url, reference=ref[0]))


def populate_POI_wiki_desc():
    pois = db_manager.query("""
    SELECT poi.id, poi.name, destination.name, destination.country_code FROM poi 
    JOIN destination ON destination.id = poi.destination_id
    WHERE wiki_description IS NULL
    """)
    for poi in pois:
        desc = wikipedia.getWikiDescription(
            poi[1])
        db_manager.insert("""
        UPDATE poi SET wiki_description = "{desc}"
        WHERE id = "{id}"
        """.format(desc=desc, id=poi[0]))


def calculate_tourist_scores():
    dests = db_manager.query("""
    SELECT id FROM destination ORDER BY population DESC LIMIT 10
    """)
    for dest in dests:
        pois = db_manager.query("""
        SELECT rating, num_ratings FROM poi
        WHERE destination_id = {dest_id}
        ORDER BY num_ratings DESC
        LIMIT 30
        """.format(dest_id=dest[0]))
        score = 0
        for poi in pois:
            score += poi[0] * poi[1]
        db_manager.insert("""
        UPDATE destination SET tourist_score = {score}
        WHERE id = {dest_id}
        """.format(score=score, dest_id=dest[0]))


def populate_POI_table():
    dests = db_manager.query("""
    SELECT id, latitude, longitude, name, country_code FROM destination WHERE city_code IS NOT NULL ORDER BY population DESC LIMIT 10
    """)
    poisForDB = []
    for dest in dests[1:10]:
        pois = google_places.get_nearby_POIs(
            dest[1], dest[2], dest[3] + "," + dest[4])
        for poi in pois:
            db_manager.insert("""
            REPLACE INTO poi (id, destination_id, name, latitude, longitude, rating, num_ratings, types)
            VALUES ("{id}", {destination_id}, "{name}", {latitude},
                    {longitude}, {rating}, {num_ratings}, "{types}")
            """.format(id=poi["place_id"], destination_id=dest[0], name=poi["name"], latitude=poi["geometry"]["location"]["lat"], longitude=poi["geometry"]["location"]["lng"], rating=poi["rating"] if "rating" in poi else "NULL", num_ratings=poi["user_ratings_total"], types=str(poi["types"]).replace('"', '').replace("'", "")))
            if "photos" in poi:
                for photo in poi["photos"]:
                    db_manager.insert("""
                    INSERT INTO poi_photo (reference, poi_id, height, width)
                    VALUES ("{reference}", "{poi_id}", {height}, {width})
                    """.format(reference=photo["photo_reference"], poi_id=poi["place_id"], height=photo["height"], width=photo["width"]))


def add_codes():
    codes_query = db_manager.query("""
    SELECT geonameid, name FROM destination_name WHERE isolanguage = "iata"
    """)
    for code in codes_query:
        ins = db_manager.insert("""
        UPDATE destination SET city_code = "{city_code}" WHERE id = {geoname_id}
        """.format(city_code=code[1], geoname_id=code[0]))


def populate_destination_images():

    dests_query = db_manager.query("""
    SELECT id,name FROM destination WHERE city_code IS NOT NULL AND culture_score IS NOT NULL ORDER BY population DESC
    """)
    missing_dest_images = get_missing_dest_images(dests_query)[:50]
    urls = pixabay.fetch_images(missing_dest_images)
    for dest_id, dest_url in urls:
        # image_insert = db_manager.insert("""
        # UPDATE destination SET image_url = "{image_url}" WHERE id = {dest_id}
        # """.format(image_url=dest_url, dest_id=dest_id))
        os.mkdir("assets/images/destinations/" + str(dest_id))
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
        headers = {'User-Agent': user_agent}
        req = urllib.request.Request(dest_url, {}, headers)
        with urllib.request.urlopen(req) as response, open("assets/images/destinations/" + str(dest_id) + "/1.jpg", 'wb') as out_file:
            data = response.read()
            out_file.write(data)


def get_missing_dest_images(dests):
    missing = []
    for dest_id, dest_name in dests:
        if not os.path.isdir("assets/images/destinations/" + str(dest_id)):
            missing.append((dest_id, dest_name))
    return missing


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
