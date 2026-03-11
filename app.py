import streamlit as st
from face_module import run_face_module
from email_leak_checker import run_email_checker
from phone_leak_checker import run_phone_checker
from dark_web_crawler import run_darkweb_search_ui

st.set_page_config(page_title="ReconSphere OSINT", layout="wide")

# === Header ===
st.title("🛡️ReconSphere: AI-Powered OSINT & Cyber Intelligence System")
st.markdown("Unified OSINT Intelligence Platform for Image Analysis, Email Breach Detection, Phone Intelligence, and Dark Web Monitoring")

# === Sidebar ===
st.sidebar.title("🧭 Navigation")
module = st.sidebar.radio("Choose a module", [
    "🖼 Reverse Image & Face Match",
    "📧 Email Leak Checker",
    "📱 Phone Number Leak Checker",
    # "🕳 Dark Web Scanner"
])

# === Route to Module ===
if module == "🖼 Reverse Image & Face Match":
    run_face_module()

elif module == "📧 Email Leak Checker":
    run_email_checker()

elif module == "📱 Phone Number Leak Checker":
    run_phone_checker()

elif module == "🕳 Dark Web Scanner":
    run_darkweb_search_ui()

# === Footer ===
st.markdown("---")
st.caption("Developed by Ashish | MCA Major Project 🔍")
