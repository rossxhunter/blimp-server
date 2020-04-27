from apis import foursquare


def get_nearby_POIs(city, query):
    return foursquare.get_nearby_POIs(
        city, query)["response"]
