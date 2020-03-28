from config import dbManager
from apis import foursquare
from apis import wikipedia


def populate_POI_details():
    dest_id = dbManager.query("""
    SELECT id FROM viable_destination WHERE name="London"
    """)[0][0]
    pois = dbManager.query("""
    SELECT id FROM poi WHERE destination_id="{dest_id} AND tip_count IS NULL"
    """.format(dest_id=dest_id))
    for poi in pois:
        poi = poi[0]
        details = foursquare.get_POI_details(poi)
        print(details)
        venue = details["response"]["venue"]
        detailsInsert = dbManager.insert("""
        UPDATE poi SET tip_count = {tip_count}, rating = {rating}, description = "{description}", best_photo = "{best_photo}"
        WHERE id = "{poi_id}"
        """.format(tip_count=venue["stats"]["tipCount"], rating=venue["rating"] if "rating" in venue else 0, description=venue["description"] if "description" in venue else "", best_photo=venue["bestPhoto"]["prefix"] + "800" + venue["bestPhoto"]["suffix"], poi_id=poi))


def populate_POI_table():
    dests = dbManager.query("""
  SELECT id, latitude, longitude FROM viable_destination WHERE name="London"
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
                dbManager.insert("""
                REPLACE INTO poi (id, name, latitude, longitude, category_id, destination_id)
                VALUES (\"{id}\", \"{name}\", {latitude}, {longitude}, \"{category_id}\", {destination_id});
                """.format(id=poiForDB["id"], name=poiForDB["name"].replace('"', '\\"'),  latitude=poiForDB["latitude"], longitude=poiForDB["longitude"], category_id=poiForDB["category_id"], destination_id=poiForDB["destination_id"]))
            print("DONE!")


def add_codes():
    codes_query = dbManager.query("""
    SELECT id,name FROM city_code;
    """)
    for code in codes_query:
        ins = dbManager.insert("""
        UPDATE destination SET city_code = \"{city_code}\" WHERE name = \"{city_name}\"                       
        """.format(city_code=code[0], city_name=code[1]))


def populate_destination_images():
    destsQuery = dbManager.query("""
    SELECT id,name FROM destination ORDER BY population DESC LIMIT 10
    """)
    for dest_id, dest_name in destsQuery:
        image = wikipedia.get_wiki_image(dest_name)
        destImageInsert = dbManager.insert("""
        UPDATE destination SET image_url = "{image_url}" WHERE id = {dest_id}
        """.format(image_url=image, dest_id=dest_id))
