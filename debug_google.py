import requests
from fake_useragent import UserAgent
import os

def debug_google_html():
    ua = UserAgent()
    headers = {"User-Agent": ua.random}
    query = "Shah Rukh Khan"
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
    
    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=10)
    
    with open("google_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print(f"Status Code: {response.status_code}")
    print("HTML saved to google_debug.html")

if __name__ == "__main__":
    debug_google_html()
