import pulp
from pulp import PULP_CBC_CMD

def swapExpandCallDaysDict(old_dict):
    new_dict = {}
    for key in old_dict:
        for val in old_dict[key]:
            new_dict[val] = key
    return new_dict

def listIntersect(list1, list2):
    intersect = [val for val in list1 if val in list2]
    return intersect