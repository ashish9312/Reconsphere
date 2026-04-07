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

def _glass_card(border_color, label, title, title_color, subtitle):
    return (
        f'<div style="background:linear-gradient(135deg,rgba(27,32,40,0.8),rgba(15,20,26,0.9));'
        f"border:1px solid rgba(114,117,125,0.15);border-left:3px solid {border_color};"
        f'border-radius:10px;padding:1rem 1.25rem;">'
        f"<p style=\"font-family:'Inter',sans-serif;font-size:0.65rem;font-weight:600;"
        f'text-transform:uppercase;letter-spacing:0.08em;color:#72757D;margin:0 0 .4rem 0;">{label}</p>'
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:0.85rem;color:{title_color};"
        f'font-weight:600;margin:0;">{title}</p>'
        f"<p style=\"font-family:'Inter',sans-serif;font-size:0.7rem;color:#A8ABB3;margin:.3rem 0 0 0;\">{subtitle}</p>"
        f"</div>"
    )

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
    st.markdown(
        '<h2 style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
        'background:linear-gradient(135deg,#00E5FF,#AF88FF);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;margin-bottom:.3rem;">'
        "📱 Phone Number Leak Checker</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Manrope\',sans-serif;font-size:.9rem;color:#A8ABB3;margin-bottom:1.5rem;">'
        "Select a country code and enter a phone number to check for offline evidence and OSINT leads.</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(32,38,47,0.5),rgba(15,20,26,0.7));'
        "backdrop-filter:blur(12px);border:1px solid rgba(114,117,125,0.15);"
        'border-radius:12px;padding:1.75rem;margin-bottom:.5rem;">'
        "<p style=\"font-family:'Inter',sans-serif;font-size:.65rem;font-weight:600;"
        'text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;">'
        "📡 PHONE INTELLIGENCE SCAN</p></div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        country_label = st.selectbox("COUNTRY CODE", list(COUNTRY_CODE_OPTIONS.keys()), index=0)
    with c2:
        phone_input = st.text_input("PHONE NUMBER", "", placeholder="9876543210")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡ CHECK FOR LEAKS", use_container_width=True) and phone_input:
        full_phone, local_digits = normalize_phone_for_lookup(
            COUNTRY_CODE_OPTIONS[country_label], phone_input
        )

        if not (7 <= len(local_digits) <= 15):
            st.warning("⚠️ Please enter a valid phone number (7-15 digits).")
            return

        if not is_valid_phone(local_digits) and len(local_digits) != 10:
            st.info("ℹ️ Non-10-digit formats are allowed for international checks.")

        st.caption(f"Normalized lookup: `{full_phone}`")
        st.markdown(
            '<h3 style="font-family:\'Space Grotesk\',sans-serif;font-weight:600;'
            'color:#81ECFF;margin-top:1.5rem;margin-bottom:1rem;">🔗 OSINT Search Links</h3>',
            unsafe_allow_html=True,
        )

        osint_links = generate_osint_dorks(full_phone)
        cols = st.columns(len(osint_links))
        for idx, (engine, url) in enumerate(osint_links.items()):
            icon = SEARCH_ENGINE_ICONS.get(engine, "🔍")
            with cols[idx]:
                st.markdown(
                    f'<a href="{url}" target="_blank" style="text-decoration:none!important;">'
                    f'<div style="background:linear-gradient(135deg,rgba(27,32,40,0.8),rgba(15,20,26,0.9));'
                    f"border:1px solid rgba(114,117,125,0.15);border-radius:10px;padding:1rem;text-align:center;"
                    f'cursor:pointer;">'
                    f'<p style="font-size:1.5rem;margin:0 0 .4rem 0;">{icon}</p>'
                    f"<p style=\"font-family:'Manrope',sans-serif;font-size:.88rem;font-weight:600;"
                    f'color:#81ECFF;margin:0 0 .2rem 0;">{engine}</p>'
                    f"<p style=\"font-family:'Inter',sans-serif;font-size:.65rem;color:#72757D;"
                    f'text-transform:uppercase;letter-spacing:.05em;margin:0;">OPEN SEARCH →</p>'
                    f"</div></a>",
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<h3 style="font-family:\'Space Grotesk\',sans-serif;font-weight:600;'
            'color:#81ECFF;margin-top:1.5rem;margin-bottom:1rem;">🛡️ Offline Leak Database</h3>',
            unsafe_allow_html=True,
        )
        offline_leaks = lookup_offline_leak(full_phone, allow_legacy_suffix_match=False)
        if offline_leaks:
            st.error(f"🚨 **BREACH DETECTED** — {len(offline_leaks)} breach sample(s):")
            for item in offline_leaks:
                safe_item = escape(str(item))
                st.markdown(
                    f'<div style="background:rgba(255,113,108,0.06);border-left:3px solid #FF716C;'
                    f"border-radius:6px;padding:.5rem .75rem;margin:.3rem 0;"
                    f"font-family:'Manrope',sans-serif;font-size:.88rem;color:#FFA8A3;\">"
                    f"● {safe_item}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(
                "ℹ️ No offline evidence found in the local database. Use OSINT links for manual verification."
            )

    st.markdown("<br>", unsafe_allow_html=True)
    i1, i2 = st.columns(2)
    with i1:
        st.markdown(_glass_card("#00E5FF", "OSINT SEARCH ENGINES", "DuckDuckGo · Bing · Google", "#F1F3FC", "Dork-based paste-site recon"), unsafe_allow_html=True)
    with i2:
        st.markdown(_glass_card("#10B981", "OFFLINE LEAK DATABASE", "● Ready to Scan", "#10B981", "Local JSON breach samples"), unsafe_allow_html=True)
