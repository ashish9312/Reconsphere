import re
import os
import json
import base64
import random
import time
import requests
from PIL import Image
from io import BytesIO
from urllib.parse import quote

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
        try:
            with open(LEAK_DB_PATH, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if isinstance(payload, dict):
                return payload
        except Exception as error:
            print(f"Error loading offline leak database: {error}")
    return {}

def lookup_offline_leak(input_data: str, allow_legacy_suffix_match: bool = False):
    """
    Search local leak database for matching email or phone
    """
    query = str(input_data or "").strip()
    if not query:
        return []

    db = load_offline_leaks()
    direct_match = db.get(query, [])
    if direct_match:
        return direct_match

    normalized_query = normalize_phone(query)
    if not normalized_query:
        return []

    candidates = {
        normalized_query,
        f"+{normalized_query}",
    }
    if query.startswith("+"):
        candidates.add(query)

    for key, leaks in db.items():
        normalized_key = normalize_phone(key)
        if not normalized_key:
            continue
        if key in candidates or normalized_key in candidates or f"+{normalized_key}" in candidates:
            return leaks

    if allow_legacy_suffix_match and len(normalized_query) >= 10:
        local_phone = normalized_query[-10:]
        for key, leaks in db.items():
            normalized_key = normalize_phone(key)
            if len(normalized_key) >= 10 and normalized_key[-10:] == local_phone:
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

def _hibp_result(
    status: str,
    breaches=None,
    message: str = "",
    http_status: int = None,
    retry_after: str = None,
):
    return {
        "status": status,
        "breaches": breaches or [],
        "message": message,
        "http_status": http_status,
        "retry_after": retry_after,
    }


def fetch_hibp_breach(email: str, api_key=None, max_retries: int = 2) -> dict:
    """
    Fetch breaches for email from Have I Been Pwned (HIBP) API
    """
    normalized_email = str(email or "").strip().lower()
    if not is_valid_email(normalized_email):
        return _hibp_result("invalid_input", message="Invalid email format")

    if not api_key:
        return _hibp_result(
            "missing_api_key",
            message="HIBP API key is required for live checks",
        )

    headers = {
        "User-Agent": "ReconSphere-Leak-Scanner",
        "hibp-api-key": api_key,
    }
    encoded_email = quote(normalized_email, safe="")
    url = (
        "https://haveibeenpwned.com/api/v3/breachedaccount/"
        f"{encoded_email}?truncateResponse=false"
    )

    backoff_seconds = 0.5
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=(3, 10))
        except requests.RequestException as error:
            if attempt < max_retries:
                time.sleep(backoff_seconds + random.uniform(0, 0.2))
                backoff_seconds *= 2
                continue
            return _hibp_result("network_error", message=str(error))

        status_code = response.status_code
        if status_code == 200:
            try:
                breaches = response.json()
            except Exception:
                breaches = []
            breach_names = [str(item.get("Name", "Unknown breach")) for item in breaches if isinstance(item, dict)]
            return _hibp_result("breached", breaches=breach_names, http_status=200)
        if status_code == 404:
            return _hibp_result("clean", breaches=[], http_status=404)
        if status_code == 400:
            return _hibp_result("invalid_input", http_status=400, message="HIBP rejected the email input")
        if status_code == 401:
            return _hibp_result("auth_error", http_status=401, message="Invalid or missing HIBP API key")
        if status_code == 403:
            return _hibp_result("forbidden", http_status=403, message="HIBP access forbidden")
        if status_code in (429, 503):
            retry_after = response.headers.get("Retry-After")
            if attempt < max_retries:
                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds
                time.sleep(wait_seconds + random.uniform(0, 0.2))
                backoff_seconds *= 2
                continue
            return _hibp_result(
                "rate_limited" if status_code == 429 else "provider_unavailable",
                http_status=status_code,
                retry_after=retry_after,
                message="HIBP temporarily unavailable",
            )

        return _hibp_result(
            "provider_error",
            http_status=status_code,
            message=f"Unexpected HIBP response ({status_code})",
        )

    return _hibp_result("provider_error", message="Unknown HIBP error")
