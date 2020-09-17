from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from OSMPythonTools.nominatim import Nominatim
from wikidata.client import Client
from config import db_manager

nominatim = Nominatim()
overpass = Overpass()
wikidata_client = Client()


def get_osm_pois(dest_id):
    dest = db_manager.query("""
    SELECT name, country_code FROM destination
    WHERE id = {dest_id}
    """.format(dest_id=dest_id))
    areaId = nominatim.query(dest[0][0] + ", " + dest[0][1]).areaId()
    query_tourism = overpassQueryBuilder(area=areaId, elementType=[
        'node'], selector='"tourism"', includeGeometry=True)

    all_tourism_pois = overpass.query(
        query_tourism, timeout=600).toJSON()["elements"]

    valid_pois = {}
    p_instance_of = wikidata_client.get('P31')
    p_image = wikidata_client.get('P18')

    for poi in all_tourism_pois:
        if "name" in poi["tags"] and poi["id"] not in valid_pois and poi["tags"]["tourism"] != "hotel":
            valid_pois[poi["id"]] = poi

    pois = list(valid_pois.values())
    for poi in pois:
        # wikidata_id = None
        # instance_of = None
        # if "wikidata" in poi["tags"]:
        #     wikidata_id = poi["tags"]["wikidata"]
        #     wikidata_entry = wikidata_client.get(
        #         wikidata_id, load=True)
        #     if p_instance_of in wikidata_entry:
        #         instance_of = wikidata_entry[p_instance_of].label.texts["en"]
        if poi["type"] == "node":
            lat = poi["lat"]
            lon = poi["lon"]
        else:
            lat = (poi["bounds"]["minlat"] + poi["bounds"]["maxlat"]) / 2
            lon = (poi["bounds"]["minlon"] + poi["bounds"]["maxlon"]) / 2
            poi["lat"] = lat
            poi["lon"] = lon
    return pois
    # db_manager.insert("""
    # REPLACE INTO poi_new (id, destination_id, original_name, latitude, longitude, wikipedia_link, instance_of)
    # VALUES ("{poi_id}", {dest_id}, "{name}", {lat}, {lon}, "{wikipedia}", {instance_of})
    # """.format(poi_id=poi["id"], dest_id=dest_id, name=poi["tags"]["name"] or "", lat=lat, lon=lon, wikipedia=poi["tags"]["wikipedia"], instance_of='"'+instance_of+'"' if instance_of != None else "NULL"))

    # if "wikidata" in poi["tags"] and p_image in wikidata_entry:
    #     wikidata_entry = wikidata_client.get(
    #         poi["tags"]["wikidata"], load=True)

    #     wikidata_image = wikidata_entry[p_image]
    #     image_url = wikidata_image.image_url
    #     width = wikidata_image.image_resolution[0]
    #     height = wikidata_image.image_resolution[1]
    #     db_manager.insert("""
    #     REPLACE INTO poi_photo_new (poi_id, url, width, height)
    #     VALUES ("{poi_id}", "{url}", {width}, {height})
    #     """.format(poi_id=poi["id"], url=image_url, width=width, height=height))
