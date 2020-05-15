from mapbox import DirectionsMatrix

service = DirectionsMatrix()


def getMatrix(features, method, sources=None, destinations=None):
    response = service.matrix(
        features, profile='mapbox/' + method, sources=sources, destinations=destinations, annotations=["duration"])
    r = response.json()
    return r["durations"]
