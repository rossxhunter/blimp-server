from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from OSMPythonTools.nominatim import Nominatim
from wikidata.client import Client

nominatim = Nominatim()
overpass = Overpass()
wikidata_client = Client()


def get_tourist_data():
    areaId = nominatim.query('Paris, France').areaId()
    query_tourism = overpassQueryBuilder(area=areaId, elementType=[
        'way', 'relation', 'node'], selector='"tourism"', includeGeometry=True)
    query_leisure = overpassQueryBuilder(area=areaId, elementType=[
        'way', 'relation', 'node'], selector='"leisure"', includeGeometry=True)

    all_tourism_pois = overpass.query(query_tourism).toJSON()["elements"]
    all_leisure_pois = overpass.query(query_leisure).toJSON()["elements"]
    valid_pois = {}

    for poi in all_tourism_pois:
        if "wikipedia" in poi["tags"] and poi["id"] not in valid_pois and poi["tags"]["tourism"] != "hotel":
            valid_pois[poi["id"]] = poi

    for poi in all_leisure_pois:
        if "wikipedia" in poi["tags"] and poi["id"] not in valid_pois:
            valid_pois[poi["id"]] = poi
    pois = list(valid_pois.values())
    entity = wikidata_client.get('Q160409', load=True)
    p_instanceof = wikidata_client.get('P31')
    att = entity[p_instanceof]
    print(att)
