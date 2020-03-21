import wikipedia


def getWikiDescription(name):
    return wikipedia.summary(name, sentences=4)
