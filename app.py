import streamlit as st

from email_leak_checker import run_email_checker
from face_module import run_face_module
from phone_leak_checker import run_phone_checker

st.set_page_config(page_title="ReconSphere OSINT", layout="wide")

st.title("ReconSphere: AI-Powered OSINT and Cyber Intelligence System")
st.markdown(
    "Unified OSINT platform for image analysis, email breach detection, and phone intelligence."
)

st.sidebar.title("Navigation")
module = st.sidebar.radio(
    "Choose a module",
    [
        "Reverse Image and Face Match",
        "Email Leak Checker",
        "Phone Number Leak Checker",
    ],
)

if module == "Reverse Image and Face Match":
    run_face_module()
elif module == "Email Leak Checker":
    run_email_checker()
elif module == "Phone Number Leak Checker":
    run_phone_checker()

st.markdown("---")
st.caption("Developed by Ashish | MCA Major Project")
