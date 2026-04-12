import hashlib
import html
import io
import json
import os
import re
import tempfile
from urllib.parse import urlparse

import requests
import streamlit as st
from PIL import Image, ImageStat

from face_compare import compare_face_profiles, extract_face_profile_from_path, get_neural_signature
from report_generator import generate_pdf_report
from reverse_search import perform_reverse_search
from utils import VALID_IMAGE_UPLOAD_TYPES, is_valid_image_file, resize_image
from intelligence_engine import engine

# Constants
RESULTS_PER_PAGE = 3
LOCAL_IMAGE_DB_DIR = os.path.join("assets", "sample_images")
LOCAL_FACE_MATCH_THRESHOLD = 65.0
THRESHOLD_CONFIG_PATH = os.path.join("models", "thresholds.json")
IDENTITY_PROFILE_PATH = os.path.join("assets", "profiles.json")
REQUIRED_PROFILE_FIELDS = ("name", "type", "description", "risk_level", "images")

SCORE_FIELDS = [
    ("Overall", "overall_score"),
    ("Recognition", "recognition_score"),
    ("Facial", "facial_score"),
    ("Eyes", "eye_score"),
    ("Lips", "lip_score"),
    ("Nose", "nose_score"),
    ("Ratio", "ratio_score"),
]

RISK_COLORS = {
    "Low Risk": "#10B981",
    "Medium Risk": "#F59E0B",
    "High Risk": "#FF716C",
}

COLOR_REFERENCE = {
    "black": (20, 20, 20),
    "white": (235, 235, 235),
    "gray": (130, 130, 130),
    "red": (190, 60, 60),
    "orange": (215, 130, 65),
    "yellow": (215, 195, 85),
    "green": (85, 165, 105),
    "cyan": (80, 170, 180),
    "blue": (80, 110, 190),
    "purple": (145, 100, 180),
    "pink": (195, 120, 165),
    "brown": (135, 95, 65),
}

# Deprecated in favor of dynamic intelligence engine
ENTITY_KNOWLEDGE_BASE = {}


def ensure_local_image_database():
    os.makedirs(LOCAL_IMAGE_DB_DIR, exist_ok=True)


def get_file_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def iter_local_image_paths(database_dir):
    if not os.path.isdir(database_dir):
        return
    for root, _, files in os.walk(database_dir):
        for filename in files:
            if is_valid_image_file(filename):
                yield os.path.join(root, filename)


def format_score(score):
    return "N/A" if score is None else f"{score:.1f}%"


def render_score_breakdown(scores):
    first_row = st.columns(4)
    second_row = st.columns(3)
    for index, (label, score_key) in enumerate(SCORE_FIELDS[:4]):
        with first_row[index]:
            st.metric(label, format_score(scores.get(score_key)))
    for index, (label, score_key) in enumerate(SCORE_FIELDS[4:]):
        with second_row[index]:
            st.metric(label, format_score(scores.get(score_key)))
    raw_similarity = scores.get("raw_similarity")
    if raw_similarity is not None:
        st.caption(f"Raw similarity: {raw_similarity:.4f}")


def normalize_filename(file_name):
    return os.path.basename(str(file_name)).strip().lower()


def load_identity_database(database_path=IDENTITY_PROFILE_PATH):
    if not os.path.isfile(database_path):
        return [], {}, []
    try:
        with open(database_path, "r", encoding="utf-8") as profile_file:
            payload = json.load(profile_file)
    except Exception as error:
        print("Error loading identity profiles:", error)
        return [], {}, []

    if isinstance(payload, dict):
        raw_profiles = payload.get("identities", [])
    elif isinstance(payload, list):
        raw_profiles = payload
    else:
        raw_profiles = []

    profiles = []
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        if any(f not in profile for f in REQUIRED_PROFILE_FIELDS):
            continue
        images = profile.get("images", [])
        if not isinstance(images, list) or not images:
            continue
        profiles.append({
            "name": str(profile["name"]),
            "type": str(profile["type"]),
            "description": str(profile["description"]),
            "risk_level": str(profile["risk_level"]),
            "images": [str(img) for img in images],
        })

    identity_index = {}
    duplicate_images = []
    for profile in profiles:
        for image_name in profile["images"]:
            normalized = normalize_filename(image_name)
            if not normalized:
                continue
            if normalized in identity_index:
                duplicate_images.append(normalized)
                continue
            identity_index[normalized] = profile

    return profiles, identity_index, duplicate_images


def resolve_identity_from_path(match_path, identity_index):
    return identity_index.get(normalize_filename(match_path))


def normalize_entity_key(text):
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", normalized).strip()


def infer_name_from_path(match_path):
    file_name = os.path.splitext(os.path.basename(str(match_path)))[0]
    cleaned = re.sub(r"[_\-]+", " ", file_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def lookup_entity_knowledge(entity_name):
    key = normalize_entity_key(entity_name)
    if not key:
        return None
    return ENTITY_KNOWLEDGE_BASE.get(key)


def map_rgb_to_color_name(rgb_tuple):
    r, g, b = rgb_tuple
    best_name = "gray"
    best_distance = float("inf")
    for color_name, (cr, cg, cb) in COLOR_REFERENCE.items():
        distance = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if distance < best_distance:
            best_distance = distance
            best_name = color_name
    return best_name


def extract_dominant_color_names(image, top_n=2):
    sampled = image.convert("RGB").resize((64, 64))
    colors = sampled.getcolors(maxcolors=64 * 64)
    if not colors:
        return []
    colors.sort(key=lambda item: item[0], reverse=True)

    names = []
    for _, rgb in colors:
        color_name = map_rgb_to_color_name(rgb)
        if color_name not in names:
            names.append(color_name)
        if len(names) >= top_n:
            break
    return names


def infer_orientation(width, height):
    if width >= height * 1.2:
        return "landscape-oriented"
    if height >= width * 1.2:
        return "portrait-oriented"
    return "square-format"


def infer_lighting(image):
    luminance = ImageStat.Stat(image.convert("L")).mean[0]
    if luminance >= 180:
        return "bright"
    if luminance <= 80:
        return "low-light"
    return "moderately lit"


def summarize_visual_context(image_path, uploaded_profile):
    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")
        width, height = rgb_image.size
        visual_context = {
            "width": width,
            "height": height,
            "orientation": infer_orientation(width, height),
            "lighting": infer_lighting(rgb_image),
            "dominant_colors": extract_dominant_color_names(rgb_image, top_n=2),
            "has_face": bool(uploaded_profile and uploaded_profile.get("embedding") is not None),
        }
    return visual_context


def format_color_phrase(color_names):
    if not color_names:
        return "mixed"
    if len(color_names) == 1:
        return color_names[0]
    return f"{color_names[0]} and {color_names[1]}"


def ensure_terminal_punctuation(sentence):
    sentence = str(sentence).strip()
    if not sentence:
        return sentence
    if sentence[-1] in {".", "!", "?"}:
        return sentence
    return f"{sentence}."


def build_unknown_object_description(vc):
    orientation = vc.get("orientation", "standard-format")
    lighting = vc.get("lighting", "moderately lit")
    colors = format_color_phrase(vc.get("dominant_colors", []))
    describe_face = "a detectable face is present" if vc.get("has_face") else "no distinct face was localized"
    
    return (
        f"This {orientation} image was captured in {lighting} conditions, "
        f"featuring a palette of {colors}. Initial sensor telemetry indicates {describe_face}. "
        "No high-confidence matches were found in the intelligence databases."
    )


def build_entity_candidate(match_path, match_score, source, identity_index):
    """
    Resolves identity using local database first, then falls back to dynamic intelligence.
    """
    identity = resolve_identity_from_path(match_path, identity_index)
    if identity:
        name = identity["name"].strip()
        report = engine.get_identity_report(name)
        return {
            "name": report["name"],
            "score": float(match_score or 0.0),
            "source": source,
            "identity": identity,
            "intelligence": report,
        }

    inferred_name = infer_name_from_path(match_path)
    report = engine.get_identity_report(inferred_name)
    
    # Only return if we found a verified identity or have a strong name inference
    if report["source"] == "Wikipedia" or len(inferred_name) > 3:
        return {
            "name": report["name"],
            "score": float(match_score or 0.0),
            "source": source,
            "identity": None,
            "intelligence": report,
        }
    return None


def select_best_entity_candidate(exact_matches, face_matches, identity_index):
    for exact_match in exact_matches:
        candidate = build_entity_candidate(
            match_path=exact_match,
            match_score=100.0,
            source="exact",
            identity_index=identity_index,
        )
        if candidate:
            return candidate

    for face_match in face_matches:
        candidate = build_entity_candidate(
            match_path=face_match["path"],
            match_score=face_match["scores"].get("overall_score", 0.0),
            source="face_similarity",
            identity_index=identity_index,
        )
        if candidate:
            return candidate
    return None


def resolve_confidence_label(candidate):
    if not candidate:
        return "low"
    if candidate["source"] == "exact":
        return "high"

    score = float(candidate.get("score") or 0.0)
    if score >= 88.0:
        return "high"
    if score >= 72.0:
        return "medium"
    return "low"


def describe_match_basis(source):
    if source == "exact":
        return "an exact hash match in the neural reference set"
    return "an AI-driven facial-similarity match"


def generate_image_description_json(
    image_path,
    uploaded_profile,
    exact_matches,
    face_matches,
    identity_index,
):
    visual_context = summarize_visual_context(image_path, uploaded_profile)
    candidate = select_best_entity_candidate(exact_matches, face_matches, identity_index)
    confidence = resolve_confidence_label(candidate)

    if candidate and confidence != "low":
        intel = candidate["intelligence"]
        title = intel["name"]
        basis = describe_match_basis(candidate["source"])
        description = (
            f"{intel['description']} \n\n"
            f"This identification is verified by {basis} with a "
            f"confidence score of {candidate['score']:.1f}%."
        )
    else:
        title = "Unknown Subject"
        description = build_unknown_object_description(visual_context)
        confidence = "low"

    return {
        "status": "success",
        "title": title,
        "description": description,
        "confidence": confidence,
        "url": candidate["intelligence"]["url"] if candidate and "intelligence" in candidate else None,
        "intelligence": candidate["intelligence"] if candidate and "intelligence" in candidate else {
            "name": title,
            "type": "Unverified",
            "description": description,
            "source": "Local Analysis"
        }
    }


def render_neural_signature_report(image):
    """
    Renders the CNN-based Neural Signature Analyst report.
    """
    signature = get_neural_signature(image)
    if not signature:
        return
    import datetime
    chrono = datetime.datetime.now().strftime("%H:%M:%S UTC")
    
    # ── Minimalist Intelligence Header ──────────────────────────────
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-top:2.5rem; border-bottom:1px solid rgba(0,245,255,0.15); padding-bottom:.8rem;">'
        f'<div style="display:flex; align-items:center;">'
        f'<span class="neural-pulse" style="width:8px; height:8px; background:#00f5ff; border-radius:50%; margin-right:12px;"></span>'
        f'<h4 style="font-family:\'Space Grotesk\',sans-serif; color:#f8fafc; margin:0; text-transform:uppercase; letter-spacing:0.05em;">Neural Signature Analyst</h4>'
        f'</div>'
        f'<p style="font-family:\'Space Grotesk\',sans-serif; font-size:0.7rem; color:#475569; margin:0;">MISSION CHRONO: {chrono}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    # ── High-Impact Intelligence Matrix ─────────────────────────────
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("IDENTITY SCORE", f"{signature['nis_score']}%")
    with m_col2:
        st.metric("SIGNATURE ID", signature["signature_id"])
    with m_col3:
        status_color = "#4ade80" if signature["biometric_status"] == "AUTHENTICATED" else "#fbbf24"
        st.markdown(
            f'<div style="background:rgba(15,23,42,0.4); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:0.5rem 1rem; height:78px; display:flex; flex-direction:column; justify-content:center;">'
            f'<p style="font-size:0.7rem; color:#94a3b8; margin:0; text-transform:uppercase; letter-spacing:0.05em;">Status</p>'
            f'<p style="font-size:1rem; color:{status_color}; font-weight:700; margin:0; font-family:\'Space Grotesk\',sans-serif;">{signature["biometric_status"]}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Distilled Intelligence Card ──────────────────────────────────
    st.markdown(
        f'<div style="position:relative; background:rgba(0,245,255,0.02); border:1px solid rgba(0,245,255,0.08); '
        f'border-radius:12px; padding:1.2rem; margin-top:1rem; overflow:hidden;">'
        f'<div class="spectral-bar"></div>'
        f'<p style="font-family:\'Inter\',sans-serif; font-size:0.8rem; color:#94a3b8; line-height:1.6; margin:0;">'
        f"<b>Biometric Intelligence Brief:</b> Subject signature has been validated via <span style='color:#00f5ff;'>Spatial-Attention CNN Architecture</span>. "
        f"Neural entropy and structural variance align with verified identity parameters. "
        f"Decryption integrity: <b>SECURE</b>.</p>"
        f'</div>',
    )


def render_formatted_description_output(description_payload):
    title = description_payload.get("title", "Unknown Object")
    description = description_payload.get("description", "")
    confidence = str(description_payload.get("confidence", "low")).strip().lower()
    confidence_label = confidence.capitalize() if confidence else "Low"
    confidence_color = {
        "high": "#10B981",
        "medium": "#F59E0B",
        "low": "#FF716C",
    }.get(confidence, "#FF716C")
    safe_title = html.escape(str(title))
    safe_description = html.escape(str(description))

    st.markdown(
        '<h3 style="font-family:\'Space Grotesk\',sans-serif;color:#81ECFF;">'
        "Description</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,rgba(27,32,40,0.85),rgba(15,20,26,0.96));'
        f'border:1px solid rgba(114,117,125,0.18);border-radius:12px;padding:1.25rem 1.35rem;'
        f'margin-bottom:1rem;">'
        f'<p style="font-family:\'Inter\',sans-serif;font-size:.68rem;letter-spacing:.05em;'
        f'color:{confidence_color};text-transform:uppercase;margin:0 0 .55rem 0;">'
        f'Confidence: {confidence_label}</p>'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.9rem;">'
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:1.18rem;font-weight:700;'
        f'color:#F1F3FC;margin:0;">{safe_title}</p>'
        + (f'<a href="{description_payload["url"]}" target="_blank" style="font-size:0.8rem; color:#81ECFF;">Source</a>' if description_payload.get("url") else '') +
        f'</div>'
        f'<p style="font-family:\'Manrope\',sans-serif;font-size:.92rem;line-height:1.7;'
        f'color:#A8ABB3;margin:0;">{safe_description}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def is_allowed_result_url(result_url):
    try:
        parsed = urlparse(str(result_url))
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            return False
        if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return False
        return True
    except Exception:
        return False


def load_runtime_threshold_config():
    config = {
        "overall_score_threshold": float(LOCAL_FACE_MATCH_THRESHOLD),
        "raw_similarity_threshold": None,
        "source": "default",
    }
    if not os.path.exists(THRESHOLD_CONFIG_PATH):
        return config

    try:
        with open(THRESHOLD_CONFIG_PATH, "r", encoding="utf-8") as threshold_file:
            payload = json.load(threshold_file)
    except Exception as error:
        print("Failed to load threshold config:", error)
        return config

    raw_threshold = payload.get("best_threshold")
    if isinstance(raw_threshold, (int, float)):
        raw_threshold = float(raw_threshold)
        if -1.0 <= raw_threshold <= 1.0:
            config["raw_similarity_threshold"] = raw_threshold
            # Calibrator emits cosine-similarity thresholds in [-1, 1].
            # When present, treat this as the primary acceptance gate unless an
            # explicit overall threshold is also provided.
            config["overall_score_threshold"] = None
            config["source"] = "calibrated"
        elif 0.0 <= raw_threshold <= 100.0:
            config["overall_score_threshold"] = raw_threshold
            config["source"] = "calibrated"

    explicit_overall = payload.get("overall_score_threshold")
    if isinstance(explicit_overall, (int, float)):
        config["overall_score_threshold"] = float(explicit_overall)
        config["source"] = "calibrated"

    return config


def score_passes_runtime_threshold(scores, threshold_config):
    overall_threshold = threshold_config.get("overall_score_threshold")
    raw_threshold = threshold_config.get("raw_similarity_threshold")

    # Fallback guard for legacy configs that specify neither threshold.
    if overall_threshold is None and raw_threshold is None:
        overall_threshold = float(LOCAL_FACE_MATCH_THRESHOLD)

    if overall_threshold is not None:
        overall_score = float(scores.get("overall_score") or 0.0)
        if overall_score < float(overall_threshold):
            return False

    if raw_threshold is not None:
        raw_similarity = scores.get("raw_similarity")
        if raw_similarity is None:
            return False
        if float(raw_similarity) < float(raw_threshold):
            return False

    return True


def evaluate_dynamic_risk(similarity_score):
    if similarity_score is None:
        return "High Risk"
    if similarity_score > 90:
        return "Low Risk"
    if 70 <= similarity_score <= 90:
        return "Medium Risk"
    return "High Risk"


def build_recommended_actions(dynamic_risk, identity_type):
    actions = ["Verify identity using at least one secondary source before action."]
    if dynamic_risk == "Low Risk":
        actions.append("Proceed with standard monitoring and keep this match on record.")
    elif dynamic_risk == "Medium Risk":
        actions.append("Flag for analyst review due to possible impersonation risk.")
    else:
        actions.append("Escalate immediately for deeper investigation and threat validation.")
    if identity_type.strip().lower() in {"celebrity", "athlete", "public figure", "actor", "performer"}:
        actions.append("Check social channels for fake account reuse or identity cloning.")
    else:
        actions.append("Cross-check related OSINT artifacts to confirm attribution.")
    return actions


def render_identity_insight_report(match_path, scores, identity_index, match_basis):
    confidence_score = scores.get("overall_score")
    dynamic_risk = evaluate_dynamic_risk(confidence_score)
    
    # Infer source for the candidate builder
    source = "exact" if "Exact" in str(match_basis) else "face_similarity"
    
    candidate = build_entity_candidate(
        match_path=match_path,
        match_score=confidence_score or 0.0,
        source=source,
        identity_index=identity_index,
    )
    
    if not candidate:
        # Fallback for unknown matches
        intel = {
            "name": "Unknown Identity",
            "type": "Unverified",
            "description": "No intelligence profile linked to this matched image.",
        }
    else:
        intel = candidate.get("intelligence", {})

    identity_type = intel.get("type", "Unknown")
    risk_color = RISK_COLORS.get(dynamic_risk, "#FF716C")

    st.markdown(
        '<h4 style="font-family:\'Space Grotesk\',sans-serif;color:#81ECFF;'
        'border-bottom:1px solid rgba(114,117,125,0.15);padding-bottom:.5rem;margin-bottom:.75rem;">'
        "Identity Insight Report</h4>",
        unsafe_allow_html=True,
    )

    name = intel.get("name", "Unknown")
    itype = intel.get("type", "Unknown")
    desc = intel.get("description", "")

    github_html = ""
    if intel.get("github"):
        github_html = (
            f'<div style="margin-top:0.75rem;"><p style="font-family:\'Inter\',sans-serif;font-size:.6rem;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:.08em;color:#BF95FF;margin:0;">GITHUB FOOTPRINT</p>'
            f'<p style="font-family:\'Manrope\',sans-serif;font-size:.85rem;margin:.2rem 0 0;">'
            f'<a href="{intel["github"]}" target="_blank" style="color:#BF95FF; text-decoration:none;">{intel["github"]} →</a></p></div>'
        )

    st.markdown(
        f'<div class="glass-card bio-card" style="padding:1.25rem;">'
        f"<div style=\"display:flex;gap:2rem;flex-wrap:wrap;\">"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">NAME</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:#F1F3FC;margin:.2rem 0 0;\">{name}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">TYPE</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:#BF95FF;margin:.2rem 0 0;\">{itype}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">RISK LEVEL</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:{risk_color};font-weight:700;margin:.2rem 0 0;\">"
        f"● {dynamic_risk}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">CONFIDENCE</p>"
        f"<p style=\"font-family:'Space Grotesk',sans-serif;font-size:.95rem;color:#81ECFF;font-weight:700;margin:.2rem 0 0;\">"
        f"{format_score(confidence_score)}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">INTEL SOURCE</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:#AF88FF;margin:.2rem 0 0;\">"
        f"{intel.get('source', 'Unknown')}</p></div>"
        f"</div>"
        f"{github_html}"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.82rem;color:#A8ABB3;margin:.75rem 0 .5rem;\">{desc}</p>"
        f"<p style=\"font-family:'Inter',sans-serif;font-size:.68rem;color:#72757D;margin:0;\">Match Basis: {match_basis}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    actions_html = "".join(
        f"<li style=\"font-family:'Manrope',sans-serif;font-size:.82rem;color:#A8ABB3;margin:.25rem 0;\">{a}</li>"
        for a in build_recommended_actions(dynamic_risk, identity_type)
    )
    st.markdown(
        f"<p style=\"font-family:'Inter',sans-serif;font-size:.65rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0 0 .3rem 0;\">RECOMMENDED ACTIONS</p>"
        f"<ul style=\"padding-left:1.2rem;margin:0;\">{actions_html}</ul>",
        unsafe_allow_html=True,
    )


def find_local_database_matches(
    uploaded_path,
    uploaded_profile,
    threshold_config,
    max_face_matches=1,
):
    exact_matches = []
    face_matches = []
    if not os.path.isdir(LOCAL_IMAGE_DB_DIR):
        return exact_matches, face_matches
    uploaded_hash = get_file_hash(uploaded_path)
    for local_path in iter_local_image_paths(LOCAL_IMAGE_DB_DIR):
        try:
            if get_file_hash(local_path) == uploaded_hash:
                return [local_path], []
            with Image.open(local_path) as local_image:
                local_rgb = local_image.convert("RGB")
                scores = compare_face_profiles(uploaded_profile, local_rgb)
            if score_passes_runtime_threshold(scores, threshold_config):
                face_matches.append({
                    "path": local_path,
                    "image": resize_image(local_rgb.copy(), 300),
                    "scores": scores,
                })
        except Exception as error:
            print("Error processing local image:", error)

    face_matches.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
    if isinstance(max_face_matches, int) and max_face_matches > 0:
        face_matches = face_matches[:max_face_matches]
    return exact_matches, face_matches


def render_local_matches(exact_matches, face_matches, identity_index):
    if not exact_matches and not face_matches:
        return

    st.markdown('<div class="entrance-anim">', unsafe_allow_html=True)
    
    if exact_matches:
        st.markdown(
            '<p class="small-caps" style="color:#4ade80; margin-bottom:1rem;">'
            "● VERIFIED EXACT HASH MATCHES</p>",
            unsafe_allow_html=True
        )
        for index, match_path in enumerate(exact_matches, start=1):
            with st.container():
                st.markdown(
                    f'<div class="glass-card bio-card" style="border-left-color:#4ade80 !important;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<p class="small-caps">Intelligence File #{index}</p>'
                    f'<span style="font-size:0.6rem; color:#4ade80; background:rgba(74,222,128,0.1); padding:2px 8px; border-radius:4px;">HASH_AUTHENTICATED</span>'
                    f'</div>'
                    f'<p style="font-family:\'Space Grotesk\', sans-serif; font-size:1.1rem; color:#f8fafc; margin:0.5rem 0;">{os.path.basename(match_path)}</p>'
                    '</div>',
                    unsafe_allow_html=True
                )
                render_identity_insight_report(
                    match_path=match_path,
                    scores={"overall_score": 100.0},
                    identity_index=identity_index,
                    match_basis="Exact hash match in offline database",
                )
                st.markdown('<div style="margin-bottom:2rem;"></div>', unsafe_allow_html=True)

    if face_matches:
        st.markdown(
            '<p class="small-caps" style="color:#00f5ff; margin:2rem 0 1rem 0;">'
            "● NEURAL-SIMILARITY DETECTIONS</p>",
            unsafe_allow_html=True
        )
        for index, match in enumerate(face_matches, start=1):
            with st.container():
                # Premium Match Card
                st.markdown(
                    f'<div class="glass-card bio-card">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<p class="small-caps">Neural Match #{index}</p>'
                    f'<span style="font-size:0.6rem; color:#00f5ff; background:rgba(0,245,255,0.1); padding:2px 8px; border-radius:4px;">BIOMETRIC_STABLE</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                m_col1, m_col2 = st.columns([1, 2])
                with m_col1:
                    st.image(match["image"], use_container_width=True)
                with m_col2:
                    render_score_breakdown(match["scores"])
                
                render_identity_insight_report(
                    match_path=match["path"],
                    scores=match["scores"],
                    identity_index=identity_index,
                    match_basis="Neural similarity analysis",
                )
                st.markdown(f'<p class="small-caps" style="font-size:0.55rem; opacity:0.5;">SOURCE: {match["path"]}</p>', unsafe_allow_html=True)
                st.markdown('<div style="margin-bottom:2.5rem;"></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_web_matches(match_results):
    total = len(match_results)
    total_pages = (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    page = st.number_input("Page", min_value=1, max_value=total_pages, step=1)
    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    paginated = match_results[start:end]

    st.markdown(
        f'<h3 style="font-family:\'Space Grotesk\',sans-serif;color:#81ECFF;">'
        f"Showing Matches ({start+1} – {min(end, total)} of {total})</h3>",
        unsafe_allow_html=True,
    )
    for index, match in enumerate(paginated, start=start + 1):
        st.image(match["image"], width=250, caption=f"Match #{index}")
        render_score_breakdown(match["scores"])
        st.markdown(f"[🔗 View Source]({match['url']})")
        st.markdown("---")


def run_face_module():
    ensure_local_image_database()
    _, identity_index, duplicate_images = load_identity_database()
    threshold_config = load_runtime_threshold_config()

    # ── Header ───────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
        'background:linear-gradient(135deg,#00E5FF,#AF88FF);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;margin-bottom:.3rem;">'
        "🖼️ Reverse Image Search + Face Match</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Manrope\',sans-serif;font-size:.9rem;color:#A8ABB3;margin-bottom:1.5rem;">'
        "Upload an image to run AI-powered face matching with intelligence-style identity insights.</p>",
        unsafe_allow_html=True,
    )

    # ── Status ───────────────────────────────────────────────────────
    st.metric("OFFLINE DATABASE", "Active")
    threshold_parts = []
    if threshold_config.get("overall_score_threshold") is not None:
        threshold_parts.append(
            f"overall >= {float(threshold_config['overall_score_threshold']):.1f}%"
        )
    if threshold_config.get("raw_similarity_threshold") is not None:
        threshold_parts.append(
            f"raw similarity >= {float(threshold_config['raw_similarity_threshold']):.3f}"
        )
    if not threshold_parts:
        threshold_parts.append(f"overall >= {float(LOCAL_FACE_MATCH_THRESHOLD):.1f}%")

    threshold_caption = f"Matching threshold: {', '.join(threshold_parts)}"
    threshold_caption += f" ({threshold_config['source']})"
    st.caption(threshold_caption)

    if duplicate_images:
        dup_display = ", ".join(sorted(set(duplicate_images)))
        st.warning(f"⚠️ Duplicate image mappings in profiles: `{dup_display}`")

    # ── Upload ───────────────────────────────────────────────────────
    uploaded_file = st.file_uploader("UPLOAD A FACE IMAGE", type=list(VALID_IMAGE_UPLOAD_TYPES))

    if uploaded_file:
        img = Image.open(uploaded_file)
        
        # UI Aspect: Center and shrink the display size
        left_pad, center_col, right_pad = st.columns([1, 1.2, 1])
        with center_col:
            # Optimize display size (e.g., max width in UI)
            st.image(img, caption="Scanning Intelligence Signature...", use_container_width=True)

        # Logic Aspect: Resize if excessively large to speed up neural processing
        max_dim = 1024
        if max(img.size) > max_dim:
            img = resize_image(img, max_size=max_dim)

        with st.spinner("🔎 Analyzing Biometric Data & Global Intelligence..."):
            file_ext = os.path.splitext(uploaded_file.name or "")[1].lower() or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                # Save the (possibly resized) image to bytes for the face engine
                img_bytes = io.BytesIO()
                img.save(img_bytes, format=img.format if img.format else 'JPEG')
                temp_file.write(img_bytes.getvalue())
                uploaded_path = temp_file.name

            try:
                uploaded_profile = extract_face_profile_from_path(uploaded_path)
                exact_matches, offline_face_matches = find_local_database_matches(
                    uploaded_path, uploaded_profile, threshold_config
                )
                description_payload = generate_image_description_json(
                    image_path=uploaded_path,
                    uploaded_profile=uploaded_profile,
                    exact_matches=exact_matches,
                    face_matches=offline_face_matches,
                    identity_index=identity_index,
                )
                render_formatted_description_output(description_payload)
                signature = get_neural_signature(img)
                render_neural_signature_report(img)
                render_local_matches(exact_matches, offline_face_matches, identity_index)

                # ── PDF Intelligence Download ──────────────────────────
                if description_payload.get("status") == "success":
                    intel = description_payload.get("intelligence", {})
                    intel_pdf = intel.get("name", "Report")
                    try:
                        pdf_data = generate_pdf_report(intel, signature)
                        st.download_button(
                            label="📥 DOWNLOAD INTELLIGENCE DOSSIER",
                            data=pdf_data,
                            file_name=f"Dossier_{intel_pdf.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key=f"dossier_btn_{intel_pdf}",
                            use_container_width=True
                        )
                    except Exception as pdf_error:
                        print(f"PDF creation failed: {pdf_error}")

                result_images = perform_reverse_search(uploaded_path)
                if not result_images:
                    if not exact_matches and not offline_face_matches:
                        st.warning("⚠️ No offline or online matches found.")
                    return

                match_results = []
                for result_url in result_images:
                    if not is_allowed_result_url(result_url):
                        continue
                    try:
                        response = requests.get(result_url, timeout=5)
                        web_image = Image.open(io.BytesIO(response.content)).convert("RGB")
                        scores = compare_face_profiles(uploaded_profile, web_image)
                        match_results.append({
                            "url": result_url,
                            "image": resize_image(web_image.copy(), 300),
                            "scores": scores,
                        })
                    except Exception as error:
                        print("Error processing image:", error)

                match_results = [
                    m
                    for m in match_results
                    if score_passes_runtime_threshold(m["scores"], threshold_config)
                ]
                if not match_results:
                    if not exact_matches and not offline_face_matches:
                        st.warning("⚠️ No faces detected in found images.")
                    return

                match_results.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
                render_web_matches(match_results)
            finally:
                if os.path.exists(uploaded_path):
                    os.remove(uploaded_path)
