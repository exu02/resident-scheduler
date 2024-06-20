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
    # Advanced Options
    with st.expander("Advanced Options"):
        n_res_day = st.number_input("The minimum number of residents on during a day shift (including the on call resident)", value=2)
        days_off_ratio = 1 / st.number_input("On average, a resident should have a day off every ___ days", value=7)
        max_consecutive = st.number_input("The maximum number of consecutive days a resident should work in the scheudle", value=5)
        consecutive_off = st.radio("Should consecutive off days be allowed?", options=["No", "Yes"]) == "Yes"

    # Basic User Inputs
    view_method = st.radio("Schedule View", options=["Calendar", "Spreadsheet"], key="view_method")
    st.write("Tip: You can create the schedule in the Calendar view for initial review. Then, switch to Spreadsheet view to see CSVs that are uploadable to Google Calendar")
    sched_year = st.selectbox("Year", range(today.year, today.year+2))
    sched_month = month_dict[st.selectbox("Month", calendar.month_name[1:], index=today.month-1)]
    days = list(range(1, calendar.monthrange(sched_year, sched_month)[1]+1))

    # Residents, call days, and requeste off days
    residents = [text.strip() for text in str(st.text_input("Residents to Schedule (comma-delimited): ", key="residents")).split(",")]
    if residents != [""]:
        col1, col2 = st.columns(2)
        with col1:
            call_days_list = [st.multiselect(f"Call dates for {res}", options=days, key=f"call_dates_{res}") for res in residents]
        callHasIntersect = warnOverlapDays(call_days_list)
        if callHasIntersect:
            st.warning("Multiple residents share a call date. Please check to see if the selected dates are correct.")
        call_days_by_res = dict(zip(residents, call_days_list))
        call_days_by_day = swapExpandDaysDict(call_days_by_res)

        with col2:
            req_off_list = [st.multiselect(f"{res}'s Requested Days Off", options=days, key=f"req_off_{res}") for res in residents]
        offHasIntersect = warnOverlapDays(req_off_list)
        if offHasIntersect:
            st.warning("Multiple residents have requested the same day off. Please check to see if this is correct.")
        req_off_by_res = dict(zip(residents, req_off_list))
        req_off_by_day = swapExpandDaysDict(req_off_by_res)
        
        call_days_exist = sum(bool(st.session_state[f"call_dates_{res}"]) for res in residents)

    st.form_submit_button(label="Create Schedule")

if call_days_exist:
    st.write("Tip: If you'd like to see alternate schedules, a simple way is to change the maximum number of consecutive shifts in the Advanced Options")
    work, status = createSchedule(
        days=days, 
        residents=residents,
        call_days_by_day=call_days_by_day,
        req_off_by_day=req_off_by_day,
        n_res_day=n_res_day,
        days_off_ratio=days_off_ratio,
        max_consecutive=max_consecutive,
        consecutive_off = consecutive_off
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
            st.write("Full Schedule:")
            calendar_df = convertCalendarToDf(calendar_events=calendar_events)
            edited_calendar = st.data_editor(calendar_df, hide_index=True)

            for res, cal_df in edited_calendar.groupby("Resident"):
                st.write(f"{res}'s Schedule (Uploadable to Google Calendar):")
                st.dataframe(cal_df.drop("Resident", axis=1), hide_index=True)
    else:
        st.write(f"{status}: Could not optimize the schedule according to the given parameters. Try revisiting the requested days off, or look in the advanced options to see if lowering the minimum resident requirements or raising the max consecutive days can help.")
    
