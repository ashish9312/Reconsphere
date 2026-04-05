import hashlib
import html
import io
import json
import os
import re

import requests
import streamlit as st
from PIL import Image, ImageStat

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

ENTITY_KNOWLEDGE_BASE = {
    "ananya panday": {
        "title": "Ananya Panday",
        "entity_type": "Actor",
        "descriptor": "an Indian actor associated with contemporary Hindi cinema",
        "known_for": "her work as a Hindi film actor in contemporary Indian cinema",
        "significance": (
            "She is a prominent figure in modern Bollywood media culture and has strong visibility "
            "across film promotions, fashion campaigns, and digital entertainment coverage."
        ),
    },
    "shah rukh khan": {
        "title": "Shah Rukh Khan",
        "entity_type": "Actor",
        "descriptor": "an Indian actor and producer associated with Hindi cinema",
        "known_for": "his long-running career as a leading actor and producer in Hindi cinema",
        "significance": (
            "He is one of the most internationally recognized Indian film personalities, with major "
            "influence on global awareness of Bollywood over multiple decades."
        ),
    },
    "shahrukh khan": {
        "title": "Shah Rukh Khan",
        "entity_type": "Actor",
        "descriptor": "an Indian actor and producer associated with Hindi cinema",
        "known_for": "his long-running career as a leading actor and producer in Hindi cinema",
        "significance": (
            "He is one of the most internationally recognized Indian film personalities, with major "
            "influence on global awareness of Bollywood over multiple decades."
        ),
    },
    "amitabh bachchan": {
        "title": "Amitabh Bachchan",
        "entity_type": "Actor",
        "descriptor": "an Indian actor and television presenter associated with Hindi cinema",
        "known_for": "his landmark contributions to Hindi cinema as an actor and television presenter",
        "significance": (
            "His performances across multiple eras helped shape mainstream Indian film history, and he "
            "remains a widely studied and referenced figure in South Asian media studies."
        ),
    },
    "amitab bachan": {
        "title": "Amitabh Bachchan",
        "entity_type": "Actor",
        "descriptor": "an Indian actor and television presenter associated with Hindi cinema",
        "known_for": "his landmark contributions to Hindi cinema as an actor and television presenter",
        "significance": (
            "His performances across multiple eras helped shape mainstream Indian film history, and he "
            "remains a widely studied and referenced figure in South Asian media studies."
        ),
    },
    "mouni roy": {
        "title": "Mouni Roy",
        "entity_type": "Actor",
        "descriptor": "an Indian performer associated with television and Hindi-language films",
        "known_for": "her work in Indian television and Hindi-language films",
        "significance": (
            "She is a visible contemporary performer whose transition from television to cinema makes her "
            "a relevant public-media identity in digital image circulation."
        ),
    },
    "taj mahal": {
        "title": "Taj Mahal",
        "entity_type": "Monument",
        "descriptor": "a 17th-century white marble mausoleum in Agra, India",
        "known_for": "being a 17th-century white marble mausoleum in Agra, India",
        "significance": (
            "Commissioned by Mughal emperor Shah Jahan, it is a UNESCO World Heritage monument and a major "
            "reference point in architectural and historical scholarship."
        ),
    },
}


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


def build_entity_candidate(match_path, match_score, source, identity_index):
    identity = resolve_identity_from_path(match_path, identity_index)
    if identity:
        name = identity["name"].strip()
        return {
            "name": name,
            "score": float(match_score or 0.0),
            "source": source,
            "identity": identity,
            "knowledge": lookup_entity_knowledge(name),
        }

    inferred_name = infer_name_from_path(match_path)
    knowledge = lookup_entity_knowledge(inferred_name)
    if not knowledge:
        return None
    return {
        "name": knowledge["title"],
        "score": float(match_score or 0.0),
        "source": source,
        "identity": None,
        "knowledge": knowledge,
    }


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
        return "an exact hash match in the offline image reference set"
    return "an offline facial-similarity match against local references"


def get_candidate_report_fields(candidate):
    if not candidate:
        return {
            "name": "Unknown Identity",
            "type": "Unknown",
            "description": "No intelligence profile linked to this matched image.",
        }

    identity = candidate.get("identity")
    if identity:
        return {
            "name": identity["name"],
            "type": identity["type"],
            "description": identity["description"],
        }

    knowledge = candidate.get("knowledge") or {}
    entity_type = knowledge.get("entity_type", "Known Entity")
    descriptor = knowledge.get("descriptor")
    title = knowledge.get("title", candidate["name"])
    if descriptor:
        description = f"{title} is {descriptor}."
    else:
        description = (
            f"{title} is known for {knowledge.get('known_for', 'public significance')}."
        )
    significance = ensure_terminal_punctuation(knowledge.get("significance", ""))
    if significance:
        description = f"{description} {significance}"

    return {
        "name": title,
        "type": entity_type,
        "description": description,
    }


def infer_match_source(match_basis):
    if "Exact" in str(match_basis):
        return "exact"
    return "face_similarity"


def build_known_entity_description(candidate, visual_context):
    knowledge = candidate["knowledge"]
    title = knowledge["title"]
    descriptor = knowledge.get(
        "descriptor",
        f"a notable {knowledge.get('entity_type', 'public figure').lower()}",
    )
    sentences = [
        f"The image shows {title}.",
        f"{title} is {descriptor} and is known for {knowledge['known_for']}.",
        ensure_terminal_punctuation(knowledge["significance"]),
        (
            f"This identification is supported by {describe_match_basis(candidate['source'])} "
            f"with an observed similarity score of {candidate['score']:.1f}%."
        ),
    ]
    return " ".join(sentences)


def build_profile_description(candidate, visual_context):
    identity = candidate["identity"] or {}
    name = candidate["name"]
    identity_type = str(identity.get("type", "Unknown")).strip()
    profile_note = ensure_terminal_punctuation(
        identity.get(
            "description",
            "The subject is indexed in the local intelligence set with limited public metadata.",
        )
    )
    sentences = [
        f"The image is assessed as {name}.",
        f"{name} appears in the local reference database under the category '{identity_type}'.",
        profile_note,
        (
            "The match corresponds to an indexed subject used for intelligence-style reference and "
            "demonstration workflows."
        ),
        (
            f"This identification is supported by {describe_match_basis(candidate['source'])} "
            f"with an observed similarity score of {candidate['score']:.1f}%."
        ),
    ]
    return " ".join(sentences)


def build_unknown_object_description(visual_context):
    colors = format_color_phrase(visual_context["dominant_colors"])
    if visual_context["has_face"]:
        face_sentence = (
            "A human face is detectable, but the system did not achieve a reliable identity match "
            "against known references."
        )
    else:
        face_sentence = (
            "No clearly detectable human face is present, so identity attribution from facial "
            "comparison is not applicable."
        )
    sentences = [
        (
            f"The image shows an unidentified subject in a {visual_context['orientation']} frame "
            f"with dimensions of {visual_context['width']} by {visual_context['height']} pixels."
        ),
        f"The scene appears {visual_context['lighting']} with dominant {colors} color tones.",
        face_sentence,
        (
            "No confident match to a known public entity or indexed local profile was established "
            "during offline analysis."
        ),
        "This output is therefore reported as an unknown object for cautious interpretation.",
    ]
    return " ".join(sentences)


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
        if candidate["knowledge"]:
            title = candidate["knowledge"]["title"]
            description = build_known_entity_description(candidate, visual_context)
        else:
            title = candidate["name"]
            description = build_profile_description(candidate, visual_context)
    else:
        title = "Unknown Object"
        description = build_unknown_object_description(visual_context)
        confidence = "low"

    return {
        "title": title,
        "description": description,
        "confidence": confidence,
    }


def render_formatted_description_output(description_payload):
    title = description_payload.get("title", "Unknown Object")
    description = description_payload.get("description", "")
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
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:1.18rem;font-weight:700;'
        f'color:#F1F3FC;margin:0 0 .9rem 0;">{safe_title}</p>'
        f'<p style="font-family:\'Manrope\',sans-serif;font-size:.92rem;line-height:1.7;'
        f'color:#A8ABB3;margin:0;">{safe_description}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


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
    candidate = build_entity_candidate(
        match_path=match_path,
        match_score=confidence_score or 0.0,
        source=infer_match_source(match_basis),
        identity_index=identity_index,
    )
    report_fields = get_candidate_report_fields(candidate)
    identity_type = report_fields["type"]
    risk_color = RISK_COLORS.get(dynamic_risk, "#FF716C")

    st.markdown(
        '<h4 style="font-family:\'Space Grotesk\',sans-serif;color:#81ECFF;'
        'border-bottom:1px solid rgba(114,117,125,0.15);padding-bottom:.5rem;margin-bottom:.75rem;">'
        "Identity Insight Report</h4>",
        unsafe_allow_html=True,
    )

    name = report_fields["name"]
    itype = report_fields["type"]
    desc = report_fields["description"]

    st.markdown(
        f'<div style="background:linear-gradient(135deg,rgba(27,32,40,0.8),rgba(15,20,26,0.9));'
        f"border:1px solid rgba(114,117,125,0.15);border-radius:10px;padding:1.25rem;margin-bottom:.75rem;\">"
        f"<div style=\"display:flex;gap:2rem;flex-wrap:wrap;\">"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">NAME</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:#F1F3FC;margin:.2rem 0 0;\">{name}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">TYPE</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:#AF88FF;margin:.2rem 0 0;\">{itype}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">RISK LEVEL</p>"
        f"<p style=\"font-family:'Manrope',sans-serif;font-size:.95rem;color:{risk_color};font-weight:700;margin:.2rem 0 0;\">"
        f"● {dynamic_risk}</p></div>"
        f"<div><p style=\"font-family:'Inter',sans-serif;font-size:.6rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.08em;color:#72757D;margin:0;\">CONFIDENCE</p>"
        f"<p style=\"font-family:'Space Grotesk',sans-serif;font-size:.95rem;color:#81ECFF;font-weight:700;margin:.2rem 0 0;\">"
        f"{format_score(confidence_score)}</p></div>"
        f"</div>"
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
                face_matches.append({
                    "path": local_path,
                    "image": resize_image(local_rgb.copy(), 300),
                    "scores": scores,
                })
        except Exception as error:
            print("Error processing local image:", error)
    face_matches.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
    return exact_matches, face_matches


def render_local_matches(exact_matches, face_matches, identity_index):
    if exact_matches:
        st.success("✅ Uploaded image already exists in the offline image database.")
        for index, match_path in enumerate(exact_matches, start=1):
            st.markdown(
                f'<h3 style="font-family:\'Space Grotesk\',sans-serif;color:#10B981;">'
                f"Offline Exact Match #{index}</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**File:** `{match_path}`")
            render_identity_insight_report(
                match_path=match_path,
                scores={"overall_score": 100.0},
                identity_index=identity_index,
                match_basis="Exact hash match in offline database",
            )
            st.markdown("---")

    if face_matches:
        st.info("🔍 Found similar face matches in the offline image database.")
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

    if duplicate_images:
        dup_display = ", ".join(sorted(set(duplicate_images)))
        st.warning(f"⚠️ Duplicate image mappings in profiles: `{dup_display}`")

    # ── Upload ───────────────────────────────────────────────────────
    uploaded_file = st.file_uploader("UPLOAD A FACE IMAGE", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_column_width=True)

        with st.spinner("🔎 Scanning offline database and online sources..."):
            uploaded_path = os.path.join("assets", "temp_uploaded.jpg")
            img.save(uploaded_path)
            uploaded_profile = extract_face_profile_from_path(uploaded_path)
            exact_matches, offline_face_matches = find_local_database_matches(
                uploaded_path, uploaded_profile
            )
            description_payload = generate_image_description_json(
                image_path=uploaded_path,
                uploaded_profile=uploaded_profile,
                exact_matches=exact_matches,
                face_matches=offline_face_matches,
                identity_index=identity_index,
            )
            render_formatted_description_output(description_payload)
            render_local_matches(exact_matches, offline_face_matches, identity_index)

            result_images = perform_reverse_search(uploaded_path)
            if not result_images:
                if not exact_matches and not offline_face_matches:
                    st.warning("⚠️ No offline or online matches found.")
                return

            match_results = []
            for result_url in result_images:
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

            match_results = [m for m in match_results if m["scores"]["overall_score"] > 0]
            if not match_results:
                if not exact_matches and not offline_face_matches:
                    st.warning("⚠️ No faces detected in found images.")
                return

            match_results.sort(key=lambda x: x["scores"]["overall_score"], reverse=True)
            render_web_matches(match_results)
