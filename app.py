import streamlit as st
import os

from email_leak_checker import run_email_checker
from face_module import run_face_module
from phone_leak_checker import run_phone_checker

st.set_page_config(
    page_title="ReconSphere — Neural OSINT",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Asset Management ────────────────────────────────────────────────
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("style.css")

# ── Sidebar Nexus ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h1 class="gradient-text">🧬 ReconSphere</h1>', unsafe_allow_html=True)
    st.caption("AI-powered OSINT PLATFORM")
    st.markdown("---")
    
    module = st.radio(
        "MODULES",
        [
            "🖼️  Face Recon",
            "📧  Email Leak Checker",
            "📱  Phone Leak Checker",
        ],
        label_visibility="visible",
    )
    
    st.markdown("---")
    st.markdown(
        """
        <div class="glass-card" style="padding: 1rem; margin-top: 0.5rem;">
            <p style="font-family:'Manrope',sans-serif; font-size:0.6rem; font-weight:600;
               text-transform:uppercase; letter-spacing:0.1em; color:#94a3b8; margin:0 0 0.5rem 0;">
               NETWORK STATUS</p>
            <div style="display:flex; align-items:center;">
                <span class="status-active"></span>
                <p style="font-family:'Inter',sans-serif; font-size:0.85rem; color:#4ade80; margin:0;">
                   Synchronized</p>
            </div>
            <p style="font-family:'Inter',sans-serif; font-size:0.65rem; color:#475569; margin-top:0.4rem;">
               v3.0 — Nexus Prime</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Main Control Center ──────────────────────────────────────────────
st.markdown(
    '<h1 class="gradient-text" style="font-size:3rem; margin-bottom:0.2rem;">ReconSphere</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="small-caps" style="color:#94a3b8; margin-top:-0.5rem; margin-bottom:2.5rem;">'
    "Unified OSINT platform for image analysis, email breach detection, and phone intelligence</p>",
    unsafe_allow_html=True,
)

# Container for the module content
module_container = st.container()

with module_container:
    if module == "🖼️  Face Recon":
        run_face_module()
    elif module == "📧  Email Leak Checker":
        run_email_checker()
    elif module == "📱  Phone Leak Checker":
        run_phone_checker()

# ── Neural Footer ───────────────────────────────────────────────────
st.markdown('<div style="margin-top: 4rem;"></div>', unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    '<p style="font-family:\'Inter\',sans-serif; font-size:0.75rem; text-align:center; '
    'color:#475569; letter-spacing:0.1em; text-transform:uppercase;">'
    "Intelligence Terminal &nbsp;|&nbsp; MCA Major Project &nbsp;|&nbsp; © 2026 Nexus Systems</p>",
    unsafe_allow_html=True,
)
