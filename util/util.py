from config import db_manager


def divide_round_up(n, d):
    return int((n + (d - 1))/d)


def merge_dicts(dict_1, dict_2):
    out_dict = dict_1.copy()
    out_dict.update(dict_2)
    return out_dict


def list_to_tuple(list):
    t = "("
    for i in list:
        t += "'" + str(i) + "'" + ","
    if t.endswith(","):
        t = t[:-1]
    return t + ")"


def list_to_str_no_brackets(list):
    result = ""
    for i in range(0, len(list)):
        result += str(list[i])
        if (i != len(list) - 1):
            result += ","
    return result


def list_to_str_no_brackets_add_speech_marks(list):
    result = ""
    for i in range(0, len(list)):
        result += '"' + str(list[i]) + '"'
        if (i != len(list) - 1):
            result += ","
    return result


def listToStr(list):
    result = "("
    for i in range(0, len(list)):
        result += str(list[i])
        if (i != len(list) - 1):
            result += ","
    result += ")"
    return result


def get_list_of_values_from_list_of_dicts(d, k):
    l = []
    for i in range(0, len(d)):
        l.append(d[i][k])
    return l


def get_origin_code(origin):
    if origin["type"] == "city":
        origin_code_query = db_manager.query("""
        SELECT city_code FROM destination WHERE id={origin_id}
        """.format(origin_id=origin["id"]))
        return origin_code_query[0][0]
    return origin["id"]
