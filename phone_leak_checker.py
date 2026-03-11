import streamlit as st
import urllib.parse

from utils import is_valid_phone, lookup_offline_leak


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
        "Check if a 10-digit phone number has been exposed in OSINT dumps or dark web mentions."
    )

    phone_input = st.text_input("Enter 10-digit phone number", "", max_chars=10)

    if st.button("Check for Leaks") and phone_input:
        if not is_valid_phone(phone_input):
            st.warning("Please enter a valid 10-digit phone number.")
            return

        st.info("Generating OSINT queries and checking known leak sources...")

        osint_links = generate_osint_dorks(phone_input)

        st.subheader("OSINT Search Links")
        for engine, url in osint_links.items():
            st.markdown(f"[{engine}]({url})")

        st.subheader("Offline Leak Database Check")
        offline_leaks = lookup_offline_leak(phone_input)

        if offline_leaks:
            st.error("Phone number found in known breach samples:")
            for item in offline_leaks:
                st.markdown(f"- {item}")
        else:
            st.success("No known leaks found in the offline database.")
