import streamlit as st
import datetime
import calendar
import pulp
from backend_helpers import *
from streamlit_calendar import calendar as st_calendar
import pandas as pd

today = datetime.date.today()
month_names = calendar.month_name[1:]
month_idx = range(1, 13)
month_dict = dict(zip(month_names, month_idx))
call_days_exist = False

st.title("PGY-1 SICU Scheduler")
st.write("Let's get started with some inputs: ")

with st.form("inputs"):
    with st.expander("Advanced Options"):
        n_res_day = st.number_input("The minimum number of residents on during a day shift (including the on call resident)", value=2)
        n_res_call = st.number_input("The minimum number of residents on during a call shift", value=1)
        days_off_ratio = 1 / st.number_input("On average, a resident should have a day off every ___ days", value=7)

    viewMethod = st.radio("Schedule View", options=["Calendar", "Spreadsheet"], key="view_method")
    sched_year = st.selectbox("Year", range(today.year, today.year+2))
    sched_month = month_dict[st.selectbox("Month", calendar.month_name[1:], index=today.month-1)]
    days = list(range(1, calendar.monthrange(sched_year, sched_month)[1]+1))

    residents = [text.strip() for text in str(st.text_input("Residents to Schedule (comma-delimited): ", key="residents")).split(",")]
    if residents != [""]:
        call_days_list = [st.multiselect(f"Call dates for {res}", options=days, key=f"call_dates_{res}") for res in residents]
        hasIntersect = warnOverlapCallDays(call_days_list)
        if hasIntersect:
            st.warning("Multiple residents share a call date. Please check to see if the selected dates are correct.")
        call_days_by_res = dict(zip(residents, call_days_list))
        call_days_by_day = swapExpandCallDaysDict(call_days_by_res)
    
        call_days_exist = sum(bool(st.session_state[f"call_dates_{res}"]) for res in residents)

    st.form_submit_button(label="Create Schedule")

if call_days_exist:
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
        calendar_options, calendar_events, custom_css = createStreamlitCalendar(
            year=sched_year, 
            month=sched_month, 
            days=days,
            residents=residents,
            work=work
        )
        if st.session_state["view_method"] == "Calendar":
            cal = st_calendar(events=calendar_events, options=calendar_options, custom_css=custom_css)
            st.write(cal)
        elif st.session_state["view_method"] == "Spreadsheet":
            st.write("Full Schedule")
            calendar_df = convertCalendarToDf(calendar_events=calendar_events)
            st.dataframe(calendar_df, hide_index=True)

            for res, cal_df in calendar_df.groupby("Resident"):
                st.write(f"{res}'s Schedule:")
                st.dataframe(cal_df.drop("Resident", axis=1), hide_index=True)
    else:
        st.write(f"{status}: Could not optimize the schedule according to the given parameters. Try looking in the advanced options to see if lowering the minimum resident requirements can help.")
    
