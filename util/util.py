def divide_round_up(n, d):
    return int((n + (d - 1))/d)


def merge_dicts(dict_1, dict_2):
    out_dict = dict_1.copy()
    out_dict.update(dict_2)
    return out_dict
