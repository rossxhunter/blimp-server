import wikipedia


def getWikiDescription(name):
    return wikipedia.summary(name, sentences=4)


def get_wiki_image(name):
    return wikipedia.page(name).images[3]
