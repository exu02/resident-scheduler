import pulp
from pulp import PULP_CBC_CMD
import datetime
import math
import pandas as pd

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

def createSchedule(
        days: list[int],
        residents: list[str], 
        call_days_by_day: dict, 
        call_days_by_res: dict,
        n_res_day: int,
        days_off_ratio: float,
        max_consecutive: int,
        consecutive_off: bool,
):
    ## Initializing static parameters
    shifts = {'day', 'call'}
    days_off = round(len(days) * days_off_ratio)
    shift_ix = [(resident, day, shift) for resident in residents for day in days for shift in shifts]
    work = pulp.LpVariable.dicts('work', shift_ix, cat=pulp.LpBinary)
    prob = pulp.LpProblem('shift', pulp.LpMaximize)

    ## Objective
    prob += sum(work[ix] for ix in shift_ix)

    ## Constraints
    # At least 2 residents during the day (including on call resident)
    for day in days:
        prob += sum(work[resident, day, 'day'] for resident in residents) >= n_res_day - sum(work[resident, day, 'call'] for resident in residents)
        # if it's not an assigned call day, don't assign a call shift
        if day not in call_days_by_day:
            prob += sum(work[resident, day, 'call'] for resident in residents) == 0
        else:
            prob += work[call_days_by_day[day], day, 'call'] == 1

    # Only one resident assigned during call shift
    for day in call_days_by_day:
        prob += sum(work[resident, day, 'call'] for resident in residents) == 1

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
        if day in call_days_by_day and day != days[-1]:
            for resident in residents:
                prob += sum(work[resident, day+1, shift] for shift in shifts) <= 1 - work[resident, day, 'call']

    # Maximum allowed consecutive shifts
    for eval_day in days[:len(days) - max_consecutive]:
        for resident in residents: 
            prob += sum(work[resident, day, shift] 
                for day in range(eval_day, eval_day + max_consecutive + 1)
                for shift in shifts) <= max_consecutive
            
    # No consecutive off days
    if not consecutive_off:
        for day in days[:-1]:
            for resident in residents:
                print()
                prob += sum(work[resident, day, shift] for shift in shifts) + sum(work[resident, day+1, shift] for shift in shifts) >= 1

    # For fairness, every resident will have approximately the same workload
    for i in range(len(residents)):
        for j in range(i+1, len(residents)):
            prob += sum(work[residents[i], day, shift] for day in days for shift in shifts) == sum(work[residents[j], day, shift] for day in days for shift in shifts)

    # Attempt to solve
    results = prob.solve(PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[results]
    return work, status

def createStreamlitCalendar(year: int, month: int, days: list[int], residents: list[str], work):
    date_fmt = "%Y-%m-%d"
    cal_resources = [{"id": resident, "resident": "SICU Interns", "title": resident} for resident in residents]
    calendar_options = {
        "editable": "true",
        "selectable": "true",
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth",
        },
        "initialDate": datetime.date(year=year, month=month, day=1).strftime(date_fmt),
        "initialView": "resourceTimelineMonth",
        "resourceGroupField": "resident",
        "resources": cal_resources,
    }

    calendar_events = []
    for day in days:
        for resident in residents:
            off = True
            if work[resident, day, 'day'].varValue:
                off = False
                event = {
                    "title": "Day",
                    "start": datetime.date(year, month, day).strftime(date_fmt),
                    "end": datetime.date(year, month, day).strftime(date_fmt),
                    "allDay": "true",
                    "resourceId": resident,
                    "backgroundColor": "blue",
                }
                calendar_events.append(event)
            if work[resident, day, 'call'].varValue:
                off = False
                event = {
                    "title": "Call",
                    "start": datetime.date(year, month, day).strftime(date_fmt),
                    "end": datetime.date(year, month, day).strftime(date_fmt),
                    "allDay": "true",
                    "resourceId": resident,
                    "backgroundColor": "orange",
                }
                calendar_events.append(event)
            if off:
                event = {
                    "title": "Off",
                    "start": datetime.date(year, month, day).strftime(date_fmt),
                    "end": datetime.date(year, month, day).strftime(date_fmt),
                    "allDay": "true",
                    "resourceId": resident,
                    "backgroundColor": "green",
                }
                calendar_events.append(event)

    custom_css="""
        .fc-event-past {
            opacity: 0.8;
        }
        .fc-event-time {
            font-style: italic;
        }
        .fc-event-title {
            font-weight: 700;
        }
        .fc-toolbar-title {
            font-size: 2rem;
        }
    """
    return calendar_options, calendar_events, custom_css

def convertCalendarToDf(calendar_events: dict):
    full_calendar_df = pd.DataFrame(calendar_events)
    full_calendar_df = full_calendar_df.rename(
        columns={
            "title": "Subject",
            "start": "Start Date",
            "end": "End Date",
            "allDay": "All Day Event",
            "resourceId": "Resident",
        }
    )
    full_calendar_df = full_calendar_df.drop("backgroundColor", axis=1)
    full_calendar_df["All Day Event"] = full_calendar_df["All Day Event"].str.upper()
    return full_calendar_df