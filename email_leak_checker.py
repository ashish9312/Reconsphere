import streamlit as st
import urllib.parse

from utils import (
    fetch_hibp_breach,
    is_valid_email,
    is_valid_phone,
    lookup_offline_leak,
)


def search_phone_osint(phone):
    """Return clickable OSINT search links for a phone number."""
    encoded = urllib.parse.quote_plus(phone)
    return {
        "DuckDuckGo": f"https://duckduckgo.com/?q={encoded}+site%3Apastebin.com+OR+site%3Aghostbin.com+OR+intitle%3A%22index+of%22+filetype%3Atxt",
        "Bing": f"https://www.bing.com/search?q={encoded}+filetype%3Atxt+OR+site%3Apastebin.com",
        "Google": f"https://www.google.com/search?q={encoded}+site%3Apastebin.com+OR+site%3Aghostbin.com",
    }


def run_email_checker():
    st.header("Email / Phone Leak Checker")
    st.markdown(
        "Check if an email or 10-digit phone number has been exposed in known data breaches or dark web mentions."
    )

    input_data = st.text_input("Enter email or 10-digit phone number", "")
    hibp_api_key = st.text_input("Optional: Enter HIBP API key", type="password")

    if st.button("Check for Breaches") and input_data:
        with st.spinner("Scanning leak sources..."):
            if is_valid_email(input_data):
                leaks = fetch_hibp_breach(input_data, hibp_api_key)
                if leaks is None:
                    st.warning("Could not verify with HIBP. Checking offline database...")
                    offline = lookup_offline_leak(input_data)
                    if offline:
                        st.error("Found in the offline breach database:")
                        for item in offline:
                            st.markdown(f"- {item}")
                    else:
                        st.success("No known breaches found.")
                elif not leaks:
                    st.success("Email not found in any breaches.")
                else:
                    st.error("Breach found:")
                    for leak in leaks:
                        st.markdown(f"- {leak}")

            elif is_valid_phone(input_data):
                osint_links = search_phone_osint(input_data)
                st.info("Generated phone OSINT search links:")
                for source, link in osint_links.items():
                    st.markdown(f"[{source}]({link})")

                offline = lookup_offline_leak(input_data)
                if offline:
                    st.error("Phone number found in offline breaches:")
                    for leak in offline:
                        st.markdown(f"- {leak}")
                else:
                    st.success("No known offline leaks detected.")

            else:
                st.warning("Please enter a valid email or a valid 10-digit phone number.")
