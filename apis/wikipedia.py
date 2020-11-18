import wikipedia
import re


def get_wiki_description(name, sentences=2):
    try:
        summary = wikipedia.summary(name, sentences=sentences)
    except:
        summary = ""
    return remove_brackets(summary).replace('  ', ' ').replace(' ,', ",").replace('"', '')


def remove_brackets(desc):
    ret = ''
    skip1c = 0
    skip2c = 0
    for i in desc:
        if i == '[':
            skip1c += 1
        elif i == '(':
            skip2c += 1
        elif i == ']' and skip1c > 0:
            skip1c -= 1
        elif i == ')'and skip2c > 0:
            skip2c -= 1
        elif skip1c == 0 and skip2c == 0:
            ret += i
    return ret


def get_wiki_image(name):
    return wikipedia.page(name).images[3]
