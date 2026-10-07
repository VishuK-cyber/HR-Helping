import streamlit as st

from agent import run_agent
from config import validate_config

st.set_page_config(page_title="HR Employee Helpdesk", page_icon="💼", layout="centered")

st.title("💼 HR Employee Helpdesk")
st.caption("Leaves, payslips and company policies — one simple agent.")

try:
    validate_config()
except ValueError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.header("Employee")
    emp_id = st.text_input("Employee ID", value=st.session_state.get("emp_id", "EMP102")).strip().upper()
    st.session_state["emp_id"] = emp_id

    st.divider()
    st.markdown("**Try:**")
    st.caption("• How many sick leaves do I have left?")
    st.caption("• What does the policy say about working from home?")
    st.caption("• What was my March salary?")
    st.caption("• I want 3 days of leave from 12 March for a family function.")
    st.caption("• Can I carry my casual leaves forward?")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask HR something...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking HR data..."):
            try:
                answer = run_agent(prompt, emp_id)
            except Exception as exc:
                answer = f"Something went wrong: `{exc}`"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
