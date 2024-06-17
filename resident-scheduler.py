import streamlit as st
import datetime
import calendar
from backend_helpers import *

today = datetime.date.today()
month_names = calendar.month_name[1:]
month_idx = range(1, 13)
month_dict = dict(zip(month_names, month_idx))



st.title("PGY-1 Scheduler")
st.write("Let's get started with some inputs: ")

with st.form("inputs"):
    sched_year = st.selectbox("Year", range(today.year, today.year+2))
    sched_month = month_dict[st.selectbox("Month", calendar.month_name[1:], index=today.month-1)]

    residents = [text.strip() for text in str(st.text_input("Residents to Schedule (comma-delimited): ", key="residents")).split(',')]
    if residents != [""]:
        call_days = [st.multiselect(f'Call dates for {res}', options=range(1, calendar.monthrange(sched_year, sched_month)[1]+1)) for res in residents]
        for i in range(len(call_days)):
            for j in range(i+1, len(call_days)):
                if listIntersect(call_days[i], call_days[j]):
                    st.warning("multiple residents share a call date - please ensure there are no repeated call dates between residents. otherwise, a value will be overwritten and potentially unintended behavior may occur")
        call_days_dict = swapExpandCallDaysDict(dict(zip(residents, call_days)))

    with st.expander("Advanced Options"):
        days_off_ratio = st.number_input("On average, a resident should have a day off every ____ days", value=7)
        days_btw_call = st.number_input("Minimum number of days between call shifts", value=4)

    submitted = st.form_submit_button(label="Create Schedule")

if submitted:
    st.write('yeet')
    
