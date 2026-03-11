import streamlit as st
import urllib.parse

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
    """Return search URLs for phone-number OSINT recon."""
    encoded = urllib.parse.quote_plus(phone)
    return {
        "DuckDuckGo": f"https://duckduckgo.com/?q={encoded}+site%3Apastebin.com+OR+site%3Aghostbin.com+OR+intitle%3A%22index+of%22+filetype%3Atxt",
        "Bing": f"https://www.bing.com/search?q={encoded}+filetype%3Atxt+OR+site%3Apastebin.com",
        "Google": f"https://www.google.com/search?q={encoded}+site%3Apastebin.com+OR+site%3Aghostbin.com",
    }


def run_phone_checker():
    st.header("Phone Number Leak Checker")
    st.markdown(
        "Select a country code and enter a 10-digit phone number to check for leaks."
    )

    country_col, number_col = st.columns([1, 3])
    with country_col:
        country_label = st.selectbox(
            "Country Code",
            list(COUNTRY_CODE_OPTIONS.keys()),
            index=0,
        )
    with number_col:
        phone_input = st.text_input(
            "Phone Number",
            "",
            max_chars=10,
            placeholder="9876543210",
        )

    if st.button("Check for Leaks") and phone_input:
        if not is_valid_phone(phone_input):
            st.warning("Please enter a valid 10-digit phone number.")
            return

        full_phone_number = f"{COUNTRY_CODE_OPTIONS[country_label]}{phone_input.strip()}"
        st.info("Generating OSINT queries and checking known leak sources...")

        osint_links = generate_osint_dorks(full_phone_number)

        st.subheader("OSINT Search Links")
        for engine, url in osint_links.items():
            st.markdown(f"[{engine}]({url})")

        st.subheader("Offline Leak Database Check")
        offline_leaks = lookup_offline_leak(full_phone_number)

        if offline_leaks:
            st.error("Phone number found in known breach samples:")
            for item in offline_leaks:
                st.markdown(f"- {item}")
        else:
            st.success("No known leaks found in the offline database.")
