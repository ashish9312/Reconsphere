import urllib.parse
import re
from html import escape
import streamlit as st
from utils import is_valid_phone, lookup_offline_leak

COUNTRY_CODE_OPTIONS = {
    "India (+91)": "+91",
    "United States / Canada (+1)": "+1",
    "United Kingdom (+44)": "+44",
    "Australia (+61)": "+61",
    "Germany (+49)": "+49",
    "France (+33)": "+33",
    "Singapore (+65)": "+65",
    "United Arab Emirates (+971)": "+971",
    "Pakistan (+92)": "+92",
    "Bangladesh (+880)": "+880",
}

def generate_osint_dorks(phone):
    quoted_phone = f"\"{phone}\""
    encoded = urllib.parse.quote_plus(quoted_phone)
    encoded_context = urllib.parse.quote_plus(f"{quoted_phone} leak OR breach OR dump")
    return {
        "DuckDuckGo": f"https://duckduckgo.com/?q={encoded_context}+site%3Apastebin.com+OR+site%3Aghostbin.com",
        "Bing": f"https://www.bing.com/search?q={encoded_context}+filetype%3Atxt+OR+site%3Apastebin.com",
        "Google": f"https://www.google.com/search?q={encoded}+site%3Apastebin.com+OR+site%3Aghostbin.com",
    }

SEARCH_ENGINE_ICONS = {"DuckDuckGo": "🦆", "Bing": "🔵", "Google": "🔍"}

def normalize_phone_for_lookup(country_code, raw_phone):
    raw_phone = str(raw_phone or "").strip()
    digits = re.sub(r"\D", "", raw_phone)
    country_digits = country_code.lstrip("+")

    if raw_phone.startswith("+"):
        full_digits = digits
    else:
        full_digits = f"{country_digits}{digits}"

    return f"+{full_digits}", digits

def run_phone_checker():
    # ── Header ───────────────────────────────────────────────────────
    st.markdown(
        '<h2 class="gradient-text" style="margin-bottom:0.3rem;">'
        "📱 Phone Number Leak Checker</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="small-caps" style="color:#A8ABB3; margin-bottom:2rem;">'
        "Select a country code and enter a phone number to check for offline evidence and OSINT leads.</p>",
        unsafe_allow_html=True,
    )

    # ── Master Scan Container ────────────────────────────────────────
    st.markdown('<div class="entrance-anim">', unsafe_allow_html=True)
    
    st.markdown(
        '<div class="glass-card" style="padding:1.75rem; margin-bottom:1.5rem;">'
        '<p class="small-caps" style="margin-bottom:1rem;">📡 PHONE INTELLIGENCE SCAN</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        country_label = st.selectbox("REGION CODE", list(COUNTRY_CODE_OPTIONS.keys()), index=0)
    with c2:
        phone_input = st.text_input("IDENTIFIER (DIGITS ONLY)", "", placeholder="9876543210")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Source Intelligence ──────────────────────────────────────────
    i1, i2 = st.columns(2)
    with i1:
        st.markdown(
            '<div class="glass-card" style="border-left: 3px solid #00F5FF !important; padding:1.2rem !important; height:110px;">'
            '<p class="small-caps" style="color:#72757D;">METHOD: OSINT ENGINES</p>'
            '<p style="font-family:\'Space Grotesk\', sans-serif; font-size:1rem; color:#f8fafc; margin:0.3rem 0;">Web Reconnaissance</p>'
            '<p style="font-size:0.75rem; color:#94a3b8; margin:0;">DuckDuckGo · Bing · Google</p>'
            '</div>',
            unsafe_allow_html=True
        )
    with i2:
        st.markdown(
            '<div class="glass-card" style="border-left: 3px solid #10B981 !important; padding:1.2rem !important; height:110px;">'
            '<p class="small-caps" style="color:#72757D;">METHOD: OFFLINE DB</p>'
            '<p style="font-family:\'Space Grotesk\', sans-serif; font-size:1rem; color:#4ade80; margin:0.3rem 0;">Identity Persistence</p>'
            '<p style="font-size:0.75rem; color:#94a3b8; margin:0;">Local JSON Intelligence Core</p>'
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡ EXECUTE NEURAL SCAN", use_container_width=True) and phone_input:
        full_phone, local_digits = normalize_phone_for_lookup(
            COUNTRY_CODE_OPTIONS[country_label], phone_input
        )

        if not (7 <= len(local_digits) <= 15):
            st.warning("⚠️ Invalid identity signature (phone digits).")
            return

        st.caption(f"Normalized identity: `{full_phone}`")
        
        # ── OSINT Results ──────────────────────────────────────────
        st.markdown(
            '<p class="small-caps" style="color:#00f5ff; margin:2rem 0 1rem 0;">'
            "● OSINT INTELLIGENCE DECRYPTION LINKS</p>",
            unsafe_allow_html=True
        )

        osint_links = generate_osint_dorks(full_phone)
        cols = st.columns(len(osint_links))
        for idx, (engine, url) in enumerate(osint_links.items()):
            icon = SEARCH_ENGINE_ICONS.get(engine, "🔍")
            with cols[idx]:
                st.markdown(
                    f'<a href="{url}" target="_blank" style="text-decoration:none!important;">'
                    f'<div class="glass-card bio-card" style="text-align:center; padding:1rem !important; cursor:pointer;">'
                    f'<p style="font-size:1.5rem; margin:0 0 .4rem 0;">{icon}</p>'
                    f"<p style=\"font-family:'Space Grotesk',sans-serif; font-size:.88rem; font-weight:600; color:#81ECFF; margin:0 0 .2rem 0;\">{engine}</p>"
                    f"<p class=\"small-caps\" style=\"color:#72757D; margin:0;\">OPEN SCAN →</p>"
                    f"</div></a>",
                    unsafe_allow_html=True,
                )

        # ── Offline Results ─────────────────────────────────────────
        st.markdown(
            '<p class="small-caps" style="color:#BF95FF; margin:2rem 0 1rem 0;">'
            "● OFFLINE LEAK PERSISTENCE REPORT</p>",
            unsafe_allow_html=True
        )
        offline_leaks = lookup_offline_leak(full_phone, allow_legacy_suffix_match=False)
        if offline_leaks:
            st.markdown(
                f'<div class="glass-card" style="border-left:4px solid #FF716C !important;">'
                f'<p class="small-caps" style="color:#FF716C;">🚨 CRITICAL: LEAK EVIDENCE DETECTED ({len(offline_leaks)})</p>',
                unsafe_allow_html=True
            )
            for item in offline_leaks:
                safe_item = escape(str(item))
                st.markdown(
                    f'<div style="background:rgba(255,113,108,0.05); border-radius:6px; padding:0.6rem 0.8rem; margin:0.4rem 0; font-family:\'Inter\',sans-serif; font-size:0.85rem; color:#FFA8A3;">'
                    f'● {safe_item}</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="glass-card" style="border-left:4px solid #4ade80 !important;">'
                '<p class="small-caps" style="color:#4ade80;">✅ STATUS: NO LOCAL DISCOVERIES</p>'
                '<p style="color:#94a3b8; font-size:0.85rem; margin-top:0.5rem;">The identity was not located in the offline leak database core.</p>'
                '</div>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)
