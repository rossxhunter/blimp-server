from mapbox import DirectionsMatrix


def getMatrix(features, method, sources=None, destinations=None):
    service = DirectionsMatrix()
    print(str(sources))
    print(str(destinations))
    response = service.matrix(
        features, profile='mapbox/' + method, sources=sources, destinations=destinations)
    print(response)
    return response
