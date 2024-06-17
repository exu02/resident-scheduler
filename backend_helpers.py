import pulp
from pulp import PULP_CBC_CMD
import datetime
import calendar
import math

def swapExpandCallDaysDict(old_dict: dict):
    new_dict = {}
    for key in old_dict:
        for val in old_dict[key]:
            new_dict[val] = key
    return new_dict

def listIntersect(list1: list, list2: list):
    intersect = [val for val in list1 if val in list2]
    return intersect

def warnOverlapCallDays(call_days_list: list):
    hasIntersect = False
    for i in range(len(call_days_list)):
            for j in range(i+1, len(call_days_list)):
                if listIntersect(call_days_list[i], call_days_list[j]):
                    hasIntersect = True
                    return hasIntersect
                
def warnCallDatesTooSoon(call_days_by_res: list, days_btw_call: int):
    callTooSoon = False
    for res in call_days_by_res:
        for i in range(len(call_days_by_res[res])):
            for j in range(i+1, len(call_days_by_res[res])):
                if call_days_by_res[res][j] - call_days_by_res[res][i] < days_btw_call:
                    callTooSoon = True
                    return callTooSoon

def createSchedule(
        month: int, 
        year: int, 
        days: list[int],
        residents: list[str], 
        call_days_by_day: dict, 
        call_days_by_res: dict,
        days_off_ratio: float, 
):
    ## Initializing static parameters
    weekend_ix = [day for day in days if datetime.date(year, month, day).weekday() in [5, 6]]
    shifts = {'day', 'call'}
    days_off = math.floor(len(days) * days_off_ratio) #+ (len(call_days_by_day) // len(residents))

    shift_idx = [(resident, day, shift) for resident in residents for day in days for shift in shifts]
    work = pulp.LpVariable.dicts('work', shift_idx, cat=pulp.LpBinary)
    prob = pulp.LpProblem('shift', pulp.LpMaximize)

    ## Objective
    prob += sum(work[idx] for idx in shift_idx)

    ## Constraints
    # At least 2 residents during the day
    for day in days:
        if day in weekend_ix:
            prob += sum(work[resident, day, 'day'] for resident in residents) == 1
        else:
            prob += sum(work[resident, day, 'day'] for resident in residents) >= 2
        # if it's not an assigned call day, don't assign a call shift
        if day not in call_days_by_day:
            prob += sum(work[resident, day, 'call'] for resident in residents) == 0
        else:
            prob += work[call_days_by_day[day], day, 'call'] == 1

    # Only one resident assigned during call shift
    # for day in call_days_by_day:
    #     prob += sum(work[resident, day, 'call'] for resident in residents) == 1

    # Residents can only work at most 1 shift a day
    for day in days:
        for resident in residents:
            prob += sum(work[resident, day, shift] for shift in shifts) <= 1

    # On average, one day off per 7 days
    for resident in residents: 
        prob += sum(work[resident, day, shift]
            for day in days
            for shift in shifts) <= len(days) - (days_off + len(call_days_by_res[resident]))

    # Day after call shift is guaranteed off
    for day in days:
        if day in call_days_by_day:
            for resident in residents:
                prob += sum(work[resident, day+1, shift] for shift in shifts) <= 1 - work[resident, day, 'call']

    # Attempt to solve
    results = prob.solve(PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[results]
    return work, status
