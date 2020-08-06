from mapbox import DirectionsMatrix
import os
import time

# tokens = [os.environ["MAPBOX_ACCESS_TOKEN"]]

# os.environ["MAPBOX_ACCESS_TOKEN"] = tokens[0]


def getMatrix(features, method, sources=None, destinations=None):
    # if os.environ["MAPBOX_ACCESS_TOKEN"] == tokens[0]:
    #     os.environ["MAPBOX_ACCESS_TOKEN"] = tokens[1]
    # elif os.environ["MAPBOX_ACCESS_TOKEN"] == tokens[1]:
    #     os.environ["MAPBOX_ACCESS_TOKEN"] = tokens[0]
    time.sleep(0.2)
    service = DirectionsMatrix()
    response = service.matrix(
        features, profile='mapbox/' + method, sources=sources, destinations=destinations, annotations=["duration"])
    r = response.json()
    if "code" not in r or r["code"] != "Ok":
        print("code")
    return r["durations"]
