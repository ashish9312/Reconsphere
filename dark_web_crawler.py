import stem.process
from stem.control import Controller
import requests
import re
import time

# Optional: Use for integration with Streamlit UI
import streamlit as st

# ==============================
# 🧠 Onion Search Engine Dorks
# ==============================

DORKS = [
    "http://onion.pet/search?q=",
    "http://onion.land/search?q=",
    "http://darkfailllnkf4vf.onion/search?q=",
    # NOTE: Some may not be up 24/7, hence try multiple.
]

def get_tor_session():
    """Starts a TOR session and returns a requests session through it."""
    session = requests.session()
    session.proxies = {
        'http':  'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    return session

def check_darkweb_for_keyword(keyword):
    """Searches dark web mirrors using keyword and returns matches."""
    results = []
    session = get_tor_session()
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    for dork in DORKS:
        try:
            search_url = dork + keyword
            response = session.get(search_url, headers=headers, timeout=15)
            if response.status_code == 200:
                found_urls = re.findall(r'(http[s]?://\S+)', response.text)
                onion_links = [url for url in found_urls if ".onion" in url]
                results.extend(onion_links)
        except Exception as e:
            print(f"[!] Dork failed: {dork} => {e}")
        time.sleep(2)  # Be polite to avoid detection/spam blocks

    return list(set(results))  # Remove duplicates

# ==============================
# ✅ Streamlit Demo Handler
# ==============================

def run_darkweb_search_ui():
    st.header("🕳 Dark Web Breach Lookup")
    st.markdown("Search for leaked email/phone mentions across .onion-based breach forums.")

    keyword = st.text_input("🔐 Enter keyword (email or phone number)")
    if st.button("Scan Dark Web") and keyword:
        with st.spinner("🔍 Crawling onion mirrors..."):
            found = check_darkweb_for_keyword(keyword)
            if found:
                st.subheader("🔗 Possible Dark Web Mentions")
                for link in found:
                    st.markdown(f"[{link}]({link})")
            else:
                st.success("✅ No mentions found on known onion mirrors.")
