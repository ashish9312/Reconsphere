import re
import os
import json
import base64
import requests
from PIL import Image
from io import BytesIO

LEAK_DB_PATH = "leak_database.json"

# ====================
# 🔐 VALIDATORS
# ====================

def is_valid_email(email: str) -> bool:
    """
    Validate email format
    """
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

def is_valid_phone(phone: str) -> bool:
    """
    Validate phone format as exactly 10 digits
    """
    return bool(re.fullmatch(r"\d{10}", phone.strip()))

def normalize_phone(phone: str) -> str:
    """
    Keep only numeric characters from a phone number
    """
    return re.sub(r"\D", "", phone)

def is_valid_image_file(filename: str) -> bool:
    """
    Check if uploaded file is a valid image file
    """
    valid_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
    return any(filename.lower().endswith(ext) for ext in valid_extensions)

# ==========================
# 📦 LOCAL DATABASE HANDLING
# ==========================

def load_offline_leaks() -> dict:
    """
    Load offline leak data from JSON file for fallback
    """
    if os.path.exists(LEAK_DB_PATH):
        with open(LEAK_DB_PATH, "r") as file:
            return json.load(file)
    return {}

def lookup_offline_leak(input_data: str):
    """
    Search local leak database for matching email or phone
    """
    db = load_offline_leaks()
    direct_match = db.get(input_data, [])
    if direct_match:
        return direct_match

    if is_valid_phone(input_data):
        normalized_input = normalize_phone(input_data)
        for key, leaks in db.items():
            normalized_key = normalize_phone(key)
            if len(normalized_key) >= 10 and normalized_key[-10:] == normalized_input:
                return leaks

    return []

# ========================
# 🧠 IMAGE UTILITY
# ========================

def convert_image_to_base64(image_path: str) -> str:
    """
    Convert image file to base64 string for API usage or storage
    """
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded

def image_to_bytes(image: Image.Image) -> bytes:
    """
    Convert PIL Image object to raw byte format
    """
    img_bytes = BytesIO()
    image.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()

def resize_image(image: Image.Image, max_size: int = 512) -> Image.Image:
    """
    Resize image to maintain aspect ratio and max size
    """
    image.thumbnail((max_size, max_size))
    return image

# ========================
# 🛡️ GENERAL UTILITIES
# ========================

def mask_sensitive(text: str, show=3) -> str:
    """
    Mask sensitive information except for the first few characters
    """
    return text[:show] + "*" * (len(text) - show)

def get_filename_from_path(path: str) -> str:
    """
    Extract filename from full file path
    """
    return os.path.basename(path)

def fetch_hibp_breach(email: str, api_key=None) -> list:
    """
    Fetch breaches for email from Have I Been Pwned (HIBP) API
    """
    try:
        headers = {
            "User-Agent": "CyberIntelX-Scanner"
        }
        if api_key:
            headers["hibp-api-key"] = api_key

        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            breaches = response.json()
            return [breach['Name'] for breach in breaches]
        elif response.status_code == 404:
            return []  # No breach
        else:
            return None
    except Exception as e:
        print(f"Error fetching breach data: {e}")
        return None
