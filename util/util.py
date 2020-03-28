def divide_round_up(n, d):
    return int((n + (d - 1))/d)


def merge_dicts(dict_1, dict_2):
    out_dict = dict_1.copy()
    out_dict.update(dict_2)
    return out_dict


def listToTuple(list):
    t = "("
    for i in list:
        t += "'" + str(i) + "'" + ","
    if t.endswith(","):
        t = t[:-1]
    return t + ")"


def listToStr(list):
    result = "("
    for i in range(0, len(list)):
        result += str(list[i])
        if (i != len(list) - 1):
            result += ","
    result += ")"
    return result
