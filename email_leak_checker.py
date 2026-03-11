import streamlit as st

from utils import fetch_hibp_breach, is_valid_email, lookup_offline_leak


def run_email_checker():
    st.header("Email Leak Checker")
    st.markdown("Check if an email has been exposed in known data breaches.")

    email_input = st.text_input("Enter email address", "")
    hibp_api_key = st.text_input("Optional: Enter HIBP API key", type="password")

    if st.button("Check for Breaches") and email_input:
        with st.spinner("Scanning leak sources..."):
            if is_valid_email(email_input):
                leaks = fetch_hibp_breach(email_input, hibp_api_key)
                if leaks is None:
                    st.warning("Could not verify with HIBP. Checking offline database...")
                    offline = lookup_offline_leak(email_input)
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
            else:
                st.warning("Please enter a valid email address.")
