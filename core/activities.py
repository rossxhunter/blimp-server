from apis import foursquare


def get_nearby_POIs(dest_1, dest_2, cats):
    return foursquare.get_nearby_POIs(
        dest_1, dest_1, cats)["response"]
