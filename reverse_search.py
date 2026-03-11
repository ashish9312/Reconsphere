import requests
import base64
import json
import os
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def perform_reverse_search(image_path):
    """
    Performs reverse image search using Bing Visual Search API
    Returns list of similar image URLs (max 10)
    """

    search_results = []

    # Load image and convert to base64
    with open(image_path, "rb") as img_file:
        image_data = img_file.read()

    headers = {
        "Ocp-Apim-Subscription-Key": "",  # No API key needed for Bing visual upload workaround
        "User-Agent": UserAgent().random,
    }

    # Bing Image Search API URL
    upload_url = "https://www.bing.com/images/searchbyimage/upload"

    try:
        # Upload image to Bing
        files = {'imgurl': ("image.jpg", image_data)}
        response = requests.post(upload_url, files=files, allow_redirects=False)

        if response.status_code == 302:
            search_url = response.headers["Location"]

            # Fetch results page
            html = requests.get(search_url, headers=headers).text
            soup = BeautifulSoup(html, "lxml")

            # Extract image links
            img_tags = soup.select("a.iusc")
            for tag in img_tags[:10]:
                try:
                    m_json = json.loads(tag.get("m"))
                    search_results.append(m_json["murl"])
                except:
                    continue
        else:
            print("Image upload to Bing failed with status:", response.status_code)

    except Exception as e:
        print("Reverse search error:", e)

    return search_results
