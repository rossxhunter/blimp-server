from config import db_manager
from apis import osm
from math import sqrt
import geopy.distance
from shapely.geometry import MultiPoint, Point


def poi_in_boundaries(dest_id, latitude, longitude):
    osm_points = osm.get_osm_pois(dest_id)
    multi_points = []
    for point in osm_points:
        multi_points.append((point["lon"], point["lat"]))
    m = MultiPoint(multi_points)
    boundaries = m.convex_hull
    return boundaries.covers(Point(longitude, latitude))


def get_city_zones(dest_id):
    osm_points = osm.get_osm_pois(dest_id)
    left = osm_points[0]["lon"]
    right = osm_points[0]["lon"]
    top = osm_points[0]["lat"]
    bottom = osm_points[0]["lat"]
    for point in osm_points:
        if point["lat"] > top:
            top = point["lat"]
        if point["lat"] < bottom:
            bottom = point["lat"]
        if point["lon"] < left:
            left = point["lon"]
        if point["lon"] > right:
            right = point["lon"]
    width = right - left
    height = top - bottom
    num_lines = 8
    # num_horizontal_lines = round(width / (width + height) * num_lines)
    # num_vertical_lines = num_lines - num_horizontal_lines
    num_horizontal_lines = 4
    num_vertical_lines = 4
    center = (top - (height / num_horizontal_lines / 2),
              left + (width / num_vertical_lines / 2))
    top_left = (top, left)
    radius = geopy.distance.distance(top_left, center).km * 1000
    zones = []
    for i in range(0, num_horizontal_lines):
        lat = top - (i+0.5) * (height / num_horizontal_lines)
        for j in range(0, num_vertical_lines):
            lon = left + (j+0.5) * (width / num_vertical_lines)
            zones.append({"latitude": lat, "longitude": lon, "radius": radius})
    return zones
