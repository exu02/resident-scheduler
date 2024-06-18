import streamlit as st
import datetime
import calendar
import pulp
from backend_helpers import *

today = datetime.date.today()
month_names = calendar.month_name[1:]
month_idx = range(1, 13)
month_dict = dict(zip(month_names, month_idx))

st.title("PGY-1 SICU Scheduler")
st.write("Let's get started with some inputs: ")

with st.form("inputs"):
    with st.expander("Advanced Options"):
        n_res_day = st.number_input("The minimum number of residents on during a day shift (including the on call resident)", value=2)
        n_res_call = st.number_input("The minimum number of residents on during a call shift", value=1)
        days_off_ratio = 1 / st.number_input("On average, a resident should have a day off every ___ days", value=7)

    sched_year = st.selectbox("Year", range(today.year, today.year+2))
    sched_month = month_dict[st.selectbox("Month", calendar.month_name[1:], index=today.month-1)]
    days = list(range(1, calendar.monthrange(sched_year, sched_month)[1]+1))

    residents = [text.strip() for text in str(st.text_input("Residents to Schedule (comma-delimited): ", key="residents")).split(",")]
    if residents != [""]:
        call_days_list = [st.multiselect(f"Call dates for {res}", options=days) for res in residents]
        hasIntersect = warnOverlapCallDays(call_days_list)
        if hasIntersect:
            st.warning("Multiple residents share a call date. Please check to see if the selected dates are correct.")
        call_days_by_res = dict(zip(residents, call_days_list))
        call_days_by_day = swapExpandCallDaysDict(call_days_by_res)

    submitted = st.form_submit_button(label="Create Schedule")


if submitted and call_days_by_day:
    work, status = createSchedule(
        month=sched_month, 
        year=sched_year, 
        days=days, 
        residents=residents,
        call_days_by_day=call_days_by_day,
        call_days_by_res=call_days_by_res,
        n_res_day=n_res_day,
        n_res_call=n_res_call,
        days_off_ratio=days_off_ratio,
    )

    if status.lower() == "optimal":
        for day in days:
            day_name = calendar.day_name[datetime.date(sched_year, sched_month, day).weekday()]
            for resident in residents:
                off = True
                if work[resident, day, "day"].varValue:
                    off = False
                    st.write(f"{day_name} July {day}, {sched_year}: {resident} on days")
                if work[resident, day, "call"].varValue:
                    off = False
                    st.write(f"{day_name} July {day}, {sched_year}: {resident} on call")
                if off:
                    st.write(f"{day_name} July {day}, {sched_year}: {resident} off")
    else:
        st.write(f"{status}: Could not optimize the schedule according to the given parameters. Try looking in the advanced options to see if lowering the minimum resident requirements can help.")
    
