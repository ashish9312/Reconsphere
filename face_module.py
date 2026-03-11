import hashlib
import io
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


def render_local_matches(exact_matches, face_matches):
    if exact_matches:
        st.success("Uploaded image already exists in the offline image database.")
        for match_path in exact_matches:
            st.markdown(f"- `{match_path}`")

    if face_matches:
        st.info("Found similar face matches in the offline image database.")
        for index, match in enumerate(face_matches, start=1):
            st.image(match["image"], width=250, caption=f"Offline Match #{index}")
            render_score_breakdown(match["scores"])
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

    st.header("Reverse Image Search + Face Match")
    st.markdown(
        "Upload an image of a person to check the offline image database and get detailed face scores before searching the web."
    )
    st.caption(f"Offline image database: `{LOCAL_IMAGE_DB_DIR}`")

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
            render_local_matches(exact_matches, offline_face_matches)

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
