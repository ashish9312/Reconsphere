import streamlit as st
from html import escape

from utils import fetch_hibp_breach, is_valid_email, lookup_offline_leak


def run_email_checker():
    # ── Header ───────────────────────────────────────────────────────
    st.markdown(
        '<h2 class="gradient-text" style="margin-bottom:0.3rem;">'
        "📧 Email Leak Checker</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="small-caps" style="color:#A8ABB3; margin-bottom:2rem;">'
        "Intelligence scan for data breach exposure</p>",
        unsafe_allow_html=True,
    )

    # ── Master Scan Container ────────────────────────────────────────
    st.markdown('<div class="entrance-anim">', unsafe_allow_html=True)
    
    st.markdown(
        '<div class="glass-card" style="padding:1.75rem; margin-bottom:1.5rem;">'
        '<p class="small-caps" style="margin-bottom:1rem;">🔍 BREACH INTELLIGENCE SCAN</p>',
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns([3, 2])
    with col1:
        email_input = st.text_input("EMAIL IDENTITY", placeholder="someone@example.com")
    with col2:
        hibp_api_key = st.text_input("HIBP API ACCESS", type="password", placeholder="Enter API key")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Source Intelligence ──────────────────────────────────────────
    src_col1, src_col2 = st.columns(2)
    with src_col1:
        st.markdown(
            '<div class="glass-card" style="border-left: 3px solid #00F5FF !important; padding:1.2rem !important;">'
            '<p class="small-caps" style="color:#72757D;">SOURCE: PRIMARY</p>'
            '<p style="font-family:\'Space Grotesk\', sans-serif; font-size:1rem; color:#f8fafc; margin:0.3rem 0;">Have I Been Pwned</p>'
            '<p style="font-size:0.75rem; color:#94a3b8; margin:0;">Live API Synchronization</p>'
            '</div>',
            unsafe_allow_html=True
        )
    with src_col2:
        st.markdown(
            '<div class="glass-card" style="border-left: 3px solid #BF95FF !important; padding:1.2rem !important;">'
            '<p class="small-caps" style="color:#72757D;">SOURCE: FALLBACK</p>'
            '<p style="font-family:\'Space Grotesk\', sans-serif; font-size:1rem; color:#f8fafc; margin:0.3rem 0;">Offline Leak DB</p>'
            '<p style="font-size:0.75rem; color:#94a3b8; margin:0;">Local JSON Intelligence</p>'
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡ EXECUTE NEURAL SCAN", use_container_width=True):
        if email_input:
            with st.spinner("🔎 Synchronizing with breach databases..."):
                if is_valid_email(email_input):
                    result = fetch_hibp_breach(email_input, hibp_api_key)
                    status = result.get("status")
                    leaks = result.get("breaches", [])

                    if status == "breached":
                        st.markdown(
                            f'<div class="glass-card" style="border-left:4px solid #FF716C !important;">'
                            f'<p class="small-caps" style="color:#FF716C;">🚨 CRITICAL: BREACH DETECTED ({len(leaks)})</p>',
                            unsafe_allow_html=True
                        )
                        for leak in leaks:
                            safe_leak = escape(str(leak))
                            st.markdown(
                                f'<div style="background:rgba(255,113,108,0.05); border-radius:6px; padding:0.6rem 0.8rem; margin:0.4rem 0; font-family:\'Inter\',sans-serif; font-size:0.85rem; color:#FFA8A3;">'
                                f'● {safe_leak}</div>',
                                unsafe_allow_html=True
                            )
                        st.markdown('</div>', unsafe_allow_html=True)
                    elif status == "clean":
                        st.markdown(
                            '<div class="glass-card" style="border-left:4px solid #4ade80 !important;">'
                            '<p class="small-caps" style="color:#4ade80;">✅ STATUS: IDENTITY SECURE</p>'
                            '<p style="color:#94a3b8; font-size:0.85rem; margin-top:0.5rem;">Email has not been identified in the HIBP live repository.</p>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        offline = lookup_offline_leak(email_input)
                        st.markdown(
                            '<div class="glass-card" style="border-left:4px solid #fbbf24 !important;">'
                            '<p class="small-caps" style="color:#fbbf24;">⚠️ SOURCE LIMITATION</p>'
                            '<p style="color:#94a3b8; font-size:0.85rem; margin-top:0.5rem;">Live verification inaccessible. Falling back to local intelligence.</p>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                        
                        if offline:
                            st.markdown(
                                '<div class="glass-card" style="border-left:4px solid #FF716C !important; margin-top:1rem;">'
                                '<p class="small-caps" style="color:#FF716C;">🚨 OFFLINE MATCH DETECTED</p>',
                                unsafe_allow_html=True
                            )
                            for item in offline:
                                safe_item = escape(str(item))
                                st.markdown(
                                    f'<div style="background:rgba(255,113,108,0.05); border-radius:6px; padding:0.6rem 0.8rem; margin:0.4rem 0; font-family:\'Inter\',sans-serif; font-size:0.85rem; color:#FFA8A3;">'
                                    f'● {safe_item}</div>',
                                    unsafe_allow_html=True
                                )
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Invalid identity signature (email).")
        else:
            st.warning("⚠️ Access denied: No identity provided.")
    
    st.markdown('</div>', unsafe_allow_html=True)
