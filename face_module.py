import hashlib
import io
import json
import os

import requests
import streamlit as st
from PIL import Image

from face_compare import compare_face_profiles, extract_face_profile_from_path
from reverse_search import perform_reverse_search
from utils import is_valid_image_file, resize_image

# Constants
RESULTS_PER_PAGE = 3
LOCAL_IMAGE_DB_DIR = os.path.join("assets", "sample_images")
LOCAL_FACE_MATCH_THRESHOLD = 65.0
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

        if any(required_field not in profile for required_field in REQUIRED_PROFILE_FIELDS):
            continue

        images = profile.get("images", [])
        if not isinstance(images, list) or not images:
            continue

        profiles.append(
            {
                "name": str(profile["name"]),
                "type": str(profile["type"]),
                "description": str(profile["description"]),
                "risk_level": str(profile["risk_level"]),
                "images": [str(image_name) for image_name in images],
            }
        )

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

    if identity_type.strip().lower() in {"celebrity", "athlete", "public figure"}:
        actions.append("Check social channels for fake account reuse or identity cloning.")
    else:
        actions.append("Cross-check related OSINT artifacts to confirm attribution.")

    return actions


def render_identity_insight_report(match_path, scores, identity_index, match_basis):
    confidence_score = scores.get("overall_score")
    dynamic_risk = evaluate_dynamic_risk(confidence_score)
    identity = resolve_identity_from_path(match_path, identity_index)
    identity_type = identity["type"] if identity else "Unknown"

    st.markdown("#### Identity Insight Report")

    if identity:
        st.markdown(f"**Name:** {identity['name']}")
        st.markdown(f"**Type:** {identity['type']}")
        st.markdown(f"**Description:** {identity['description']}")
        st.markdown(
            f"**Risk Level:** {dynamic_risk} (Profile Baseline: {identity['risk_level']})"
        )
    else:
        st.markdown("**Name:** Unknown Identity (Not mapped in profiles database)")
        st.markdown("**Type:** Unknown")
        st.markdown(
            "**Description:** No intelligence profile is linked to this matched image filename."
        )
        st.markdown(f"**Risk Level:** {dynamic_risk}")

    st.markdown(f"**Confidence Score:** {format_score(confidence_score)}")
    st.markdown(f"**Match Basis:** {match_basis}")
    st.markdown("**Recommended Actions:**")
    for action in build_recommended_actions(dynamic_risk, identity_type):
        st.markdown(f"- {action}")


def find_local_database_matches(uploaded_path, uploaded_profile):
    exact_matches = []
    face_matches = []

    if not os.path.isdir(LOCAL_IMAGE_DB_DIR):
        return exact_matches, face_matches

    uploaded_hash = get_file_hash(uploaded_path)

    for local_path in iter_local_image_paths(LOCAL_IMAGE_DB_DIR):
        try:
            if get_file_hash(local_path) == uploaded_hash:
                exact_matches.append(local_path)
                continue

            with Image.open(local_path) as local_image:
                local_rgb = local_image.convert("RGB")
                scores = compare_face_profiles(uploaded_profile, local_rgb)

            if scores["overall_score"] >= LOCAL_FACE_MATCH_THRESHOLD:
                face_matches.append(
                    {
                        "path": local_path,
                        "image": resize_image(local_rgb.copy(), 300),
                        "scores": scores,
                    }
                )
        except Exception as error:
            print("Error processing local image:", error)

    face_matches.sort(key=lambda item: item["scores"]["overall_score"], reverse=True)
    return exact_matches, face_matches


def render_local_matches(exact_matches, face_matches, identity_index):
    if exact_matches:
        st.success("Uploaded image already exists in the offline image database.")
        for index, match_path in enumerate(exact_matches, start=1):
            st.markdown(f"### Offline Exact Match #{index}")
            st.markdown(f"**File:** `{match_path}`")
            render_identity_insight_report(
                match_path=match_path,
                scores={"overall_score": 100.0},
                identity_index=identity_index,
                match_basis="Exact hash match in offline database",
            )
            st.markdown("---")

    if face_matches:
        st.info("Found similar face matches in the offline image database.")
        for index, match in enumerate(face_matches, start=1):
            st.image(match["image"], width=250, caption=f"Offline Match #{index}")
            render_score_breakdown(match["scores"])
            render_identity_insight_report(
                match_path=match["path"],
                scores=match["scores"],
                identity_index=identity_index,
                match_basis="Offline face similarity match",
            )
            st.markdown(f"**File:** `{match['path']}`")
            st.markdown("---")


def render_web_matches(match_results):
    total_results = len(match_results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    page = st.number_input("Page", min_value=1, max_value=total_pages, step=1)

    start_idx = (page - 1) * RESULTS_PER_PAGE
    end_idx = start_idx + RESULTS_PER_PAGE
    paginated_results = match_results[start_idx:end_idx]

    st.markdown(
        f"### Showing Matches ({start_idx + 1} - {min(end_idx, total_results)} of {total_results})"
    )

    for index, match in enumerate(paginated_results, start=start_idx + 1):
        st.image(match["image"], width=250, caption=f"Match #{index}")
        render_score_breakdown(match["scores"])
        st.markdown(f"[View Source]({match['url']})")
        st.markdown("---")


def run_face_module():
    ensure_local_image_database()
    identity_profiles, identity_index, duplicate_images = load_identity_database()

    st.header("Reverse Image Search + Face Match")
    st.markdown(
        "Upload an image to run offline face matching with intelligence-style identity insights, then continue with web search."
    )
    st.caption(f"Offline image database: `{LOCAL_IMAGE_DB_DIR}`")
    st.caption(
        f"Identity profile database: `{IDENTITY_PROFILE_PATH}` | Loaded profiles: {len(identity_profiles)}"
    )

    if duplicate_images:
        duplicate_display = ", ".join(sorted(set(duplicate_images)))
        st.warning(
            "Duplicate image mappings detected in profiles database. "
            f"First mapping retained for: `{duplicate_display}`"
        )

    uploaded_file = st.file_uploader("Upload a face image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_column_width=True)

        with st.spinner("Checking offline image database and online sources..."):
            uploaded_path = os.path.join("assets", "temp_uploaded.jpg")
            img.save(uploaded_path)

            uploaded_profile = extract_face_profile_from_path(uploaded_path)
            exact_matches, offline_face_matches = find_local_database_matches(
                uploaded_path,
                uploaded_profile,
            )
            render_local_matches(exact_matches, offline_face_matches, identity_index)

            result_images = perform_reverse_search(uploaded_path)
            if not result_images:
                if not exact_matches and not offline_face_matches:
                    st.warning("No offline or online matches found.")
                return

            match_results = []
            for result_url in result_images:
                try:
                    response = requests.get(result_url, timeout=5)
                    web_image = Image.open(io.BytesIO(response.content)).convert("RGB")
                    scores = compare_face_profiles(uploaded_profile, web_image)
                    match_results.append(
                        {
                            "url": result_url,
                            "image": resize_image(web_image.copy(), 300),
                            "scores": scores,
                        }
                    )
                except Exception as error:
                    print("Error processing image:", error)

            match_results = [
                match for match in match_results if match["scores"]["overall_score"] > 0
            ]

            if not match_results:
                if not exact_matches and not offline_face_matches:
                    st.warning("No faces detected in found images.")
                return

            match_results.sort(key=lambda item: item["scores"]["overall_score"], reverse=True)
            render_web_matches(match_results)
