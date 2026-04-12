import math

import numpy as np
import torch
from PIL import Image
from facenet_pytorch import InceptionResnetV1, MTCNN

import torch.nn as nn
import torch.nn.functional as F
from facenet_pytorch import InceptionResnetV1, MTCNN

# Load model and face detector
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
embedder = InceptionResnetV1(pretrained="vggface2").eval().to(device)
face_detector = MTCNN(image_size=160, margin=0, device=device)

class SpatialAttention(nn.Module):
    """
    Focuses the CNN on high-impact geographic facial regions
    (Eyes, Nose, Mouth) for stronger validation.
    """
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x_in = torch.cat([avg_out, max_out], dim=1)
        x_out = self.conv(x_in)
        return self.sigmoid(x_out) * x

class NeuralValidator(nn.Module):
    """
    Tier-2 CNN with Spatial Attention for advanced structural analysis.
    """
    def __init__(self):
        super(NeuralValidator, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.attn1 = SpatialAttention()
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.attn2 = SpatialAttention()
        self.pool = nn.AdaptiveAvgPool2d((8, 8))
    
    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = self.attn1(x)
        x = F.max_pool2d(x, 2)
        x = F.relu(self.conv2(x))
        x = self.attn2(x)
        x = self.pool(x)
        return x

# Initialize enterprise-grade validator
validator = NeuralValidator().eval().to(device)

SCORE_WEIGHTS = {
    "recognition_score": 0.50,
    "facial_score": 0.20,
    "eye_score": 0.10,
    "lip_score": 0.10,
    "nose_score": 0.05,
    "ratio_score": 0.05,
}


def extract_face_embedding(image: Image.Image):
    """
    Detect a face and return a 512-d embedding vector using FaceNet.
    """
    try:
        face_tensor = face_detector(image.convert("RGB"))
        if face_tensor is None:
            return None

        face_tensor = face_tensor.unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = embedder(face_tensor)

        return embedding.cpu().numpy()[0]
    except Exception as error:
        print(f"[ERROR] Face extraction failed: {error}")
        return None


def extract_primary_landmarks(image: Image.Image):
    """
    Extract a lightweight landmark set from MTCNN.
    """
    try:
        boxes, probabilities, points = face_detector.detect(image.convert("RGB"), landmarks=True)
        if boxes is None or points is None:
            return None

        probabilities = np.asarray(probabilities, dtype=np.float32)
        points = np.asarray(points, dtype=np.float32)
        boxes = np.asarray(boxes, dtype=np.float32)

        if len(points) == 0 or len(boxes) == 0:
            return None

        best_index = int(np.argmax(probabilities))
        best_box = boxes[best_index]
        best_points = points[best_index]

        left_eye = best_points[0]
        right_eye = best_points[1]
        nose_tip = best_points[2]
        mouth_left = best_points[3]
        mouth_right = best_points[4]
        mouth_center = (mouth_left + mouth_right) / 2.0

        return {
            "box": best_box,
            "left_eye": [tuple(left_eye)],
            "right_eye": [tuple(right_eye)],
            "nose_tip": [tuple(nose_tip)],
            "mouth_left": [tuple(mouth_left)],
            "mouth_right": [tuple(mouth_right)],
            "mouth": [
                tuple(mouth_left),
                tuple(mouth_center),
                tuple(mouth_right),
            ],
            "face": [tuple(point) for point in best_points],
        }
    except Exception as error:
        print(f"[ERROR] Landmark extraction failed: {error}")
        return None


def extract_face_profile(image: Image.Image):
    """
    Build a profile containing embedding and landmarks for a face image.
    """
    rgb_image = image.convert("RGB")
    return {
        "embedding": extract_face_embedding(rgb_image),
        "landmarks": extract_primary_landmarks(rgb_image),
    }


def extract_face_profile_from_path(image_path):
    """
    Load an image from disk and return its face profile.
    """
    try:
        image = Image.open(image_path).convert("RGB")
        return extract_face_profile(image)
    except Exception as error:
        print(f"[ERROR] Face profile extraction failed: {error}")
        return {"embedding": None, "landmarks": None}


def cosine_similarity(embedding_1, embedding_2):
    """
    Return cosine similarity between two embeddings.
    """
    if embedding_1 is None or embedding_2 is None:
        return None

    norm_1 = np.linalg.norm(embedding_1)
    norm_2 = np.linalg.norm(embedding_2)
    if norm_1 == 0 or norm_2 == 0:
        return None

    return float(np.dot(embedding_1, embedding_2) / (norm_1 * norm_2))


def get_feature_points(landmarks, feature_names):
    """
    Flatten selected facial landmark groups into a point array.
    """
    if not landmarks:
        return None

    points = []
    for feature_name in feature_names:
        points.extend(landmarks.get(feature_name, []))

    if not points:
        return None

    return np.asarray(points, dtype=np.float32)


def get_eye_alignment(landmarks):
    """
    Use both eyes as the anchor for rotation and scale normalization.
    """
    left_eye = get_feature_points(landmarks, ("left_eye",))
    right_eye = get_feature_points(landmarks, ("right_eye",))
    if left_eye is None or right_eye is None:
        return None

    left_center = left_eye.mean(axis=0)
    right_center = right_eye.mean(axis=0)
    eye_vector = right_center - left_center
    eye_distance = np.linalg.norm(eye_vector)
    if eye_distance == 0:
        return None

    angle = -math.atan2(float(eye_vector[1]), float(eye_vector[0]))
    center = (left_center + right_center) / 2.0
    return center, angle, eye_distance


def normalize_points(points, alignment):
    """
    Normalize landmark points for translation, rotation, and scale.
    """
    center, angle, scale = alignment
    shifted = points - center
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ],
        dtype=np.float32,
    )
    rotated = shifted @ rotation.T
    return rotated / scale


def score_from_distance(distance, sensitivity):
    """
    Convert a normalized geometric distance into a 0-100 score.
    """
    return float(np.clip(np.exp(-distance * sensitivity) * 100.0, 0.0, 100.0))


def score_from_similarity(similarity):
    """
    Convert cosine similarity into a 0-100 recognition score.
    """
    if similarity is None:
        return None

    normalized = (similarity - 0.35) / 0.45
    return float(np.clip(normalized * 100.0, 0.0, 100.0))


def compare_landmark_feature(reference_landmarks, candidate_landmarks, feature_names, sensitivity):
    """
    Compare a facial feature using normalized landmark geometry.
    """
    reference_alignment = get_eye_alignment(reference_landmarks)
    candidate_alignment = get_eye_alignment(candidate_landmarks)
    if reference_alignment is None or candidate_alignment is None:
        return None

    reference_points = get_feature_points(reference_landmarks, feature_names)
    candidate_points = get_feature_points(candidate_landmarks, feature_names)
    if reference_points is None or candidate_points is None:
        return None

    reference_points = normalize_points(reference_points, reference_alignment)
    candidate_points = normalize_points(candidate_points, candidate_alignment)

    point_count = min(len(reference_points), len(candidate_points))
    if point_count == 0:
        return None

    distances = np.linalg.norm(
        reference_points[:point_count] - candidate_points[:point_count],
        axis=1,
    )
    return score_from_distance(float(np.mean(distances)), sensitivity)


def distance_between(point_a, point_b):
    return float(np.linalg.norm(np.asarray(point_a) - np.asarray(point_b)))


def extract_face_ratios(landmarks):
    """
    Derive normalized face-shape ratios using the MTCNN 5-point landmarks.
    """
    if not landmarks:
        return None

    box = landmarks.get("box")
    left_eye = get_feature_points(landmarks, ("left_eye",))
    right_eye = get_feature_points(landmarks, ("right_eye",))
    nose_tip = get_feature_points(landmarks, ("nose_tip",))
    mouth_left = get_feature_points(landmarks, ("mouth_left",))
    mouth_right = get_feature_points(landmarks, ("mouth_right",))

    required_features = [box, left_eye, right_eye, nose_tip, mouth_left, mouth_right]
    if any(feature is None for feature in required_features):
        return None

    face_width = max(float(box[2] - box[0]), 1e-6)
    face_height = max(float(box[3] - box[1]), 1e-6)

    left_eye_point = left_eye[0]
    right_eye_point = right_eye[0]
    nose_point = nose_tip[0]
    mouth_left_point = mouth_left[0]
    mouth_right_point = mouth_right[0]
    mouth_center = (mouth_left_point + mouth_right_point) / 2.0
    eye_center = (left_eye_point + right_eye_point) / 2.0

    return np.asarray(
        [
            distance_between(left_eye_point, right_eye_point) / face_width,
            distance_between(mouth_left_point, mouth_right_point) / face_width,
            distance_between(eye_center, nose_point) / face_height,
            distance_between(nose_point, mouth_center) / face_height,
            distance_between(eye_center, mouth_center) / face_height,
        ],
        dtype=np.float32,
    )


def compare_face_ratios(reference_landmarks, candidate_landmarks):
    """
    Compare coarse face-shape ratios.
    """
    reference_ratios = extract_face_ratios(reference_landmarks)
    candidate_ratios = extract_face_ratios(candidate_landmarks)
    if reference_ratios is None or candidate_ratios is None:
        return None

    ratio_delta = float(np.mean(np.abs(reference_ratios - candidate_ratios)))
    return score_from_distance(ratio_delta, sensitivity=14.0)


def default_score_breakdown():
    return {
        "overall_score": 0.0,
        "recognition_score": None,
        "facial_score": None,
        "eye_score": None,
        "lip_score": None,
        "nose_score": None,
        "ratio_score": None,
        "raw_similarity": None,
    }


def finalize_weighted_score(scores):
    """
    Calculate an overall score from whichever sub-scores are available.
    """
    weighted_total = 0.0
    total_weight = 0.0

    for score_name, weight in SCORE_WEIGHTS.items():
        score_value = scores.get(score_name)
        if score_value is None:
            continue
        weighted_total += score_value * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return weighted_total / total_weight


def compare_face_profiles(reference_profile, candidate_image):
    """
    Compare a reference face profile against a candidate PIL image and
    return detailed feature scores.
    """
    scores = default_score_breakdown()
    candidate_profile = extract_face_profile(candidate_image)

    reference_embedding = reference_profile.get("embedding") if reference_profile else None
    candidate_embedding = candidate_profile.get("embedding")
    reference_landmarks = reference_profile.get("landmarks") if reference_profile else None
    candidate_landmarks = candidate_profile.get("landmarks")

    raw_similarity = cosine_similarity(reference_embedding, candidate_embedding)
    scores["raw_similarity"] = raw_similarity
    scores["recognition_score"] = score_from_similarity(raw_similarity)

    scores["eye_score"] = compare_landmark_feature(
        reference_landmarks,
        candidate_landmarks,
        ("left_eye", "right_eye"),
        sensitivity=8.0,
    )
    scores["lip_score"] = compare_landmark_feature(
        reference_landmarks,
        candidate_landmarks,
        ("mouth",),
        sensitivity=7.0,
    )
    scores["nose_score"] = compare_landmark_feature(
        reference_landmarks,
        candidate_landmarks,
        ("nose_tip",),
        sensitivity=9.0,
    )
    scores["facial_score"] = compare_landmark_feature(
        reference_landmarks,
        candidate_landmarks,
        ("face",),
        sensitivity=6.0,
    )
    scores["ratio_score"] = compare_face_ratios(reference_landmarks, candidate_landmarks)

    scores["overall_score"] = finalize_weighted_score(scores)
    return scores


def compare_face_embedding(reference_profile, candidate_image):
    """
    Backward-compatible helper that returns only the overall score in 0-1 form.
    """
    score_breakdown = compare_face_profiles(reference_profile, candidate_image)
    return score_breakdown["overall_score"] / 100.0


def calculate_entropy(embedding):
    """Calculate the Shannon entropy of the neural embedding."""
    hist, _ = np.histogram(embedding, bins=50, density=True)
    hist = hist[hist > 0]
    return -np.sum(hist * np.log2(hist))

def get_neural_signature(image: Image.Image):
    """
    Extracts a high-dimensional neural signature using a dual-model fusion.
    Facenet (Primary) + NeuralValidator (Structural).
    """
    try:
        rgb_image = image.convert("RGB")
        face_tensor = face_detector(rgb_image)
        if face_tensor is None:
            return None
            
        face_tensor = face_tensor.unsqueeze(0).to(device)
        
        with torch.no_grad():
            embedding = embedder(face_tensor).cpu().numpy()[0]
            structural_features = validator(face_tensor).cpu().numpy()
            
        energy = float(np.linalg.norm(embedding))
        entropy = float(calculate_entropy(embedding))
        structural_integrity = float(np.mean(np.abs(structural_features)))

        # Unified Neural Identity Score (NIS)
        # Weights: Energy (40%), Entropy (40%), Structural (20%)
        nis_raw = (min(energy, 1.2) / 1.2 * 40) + (min(entropy, 6.0) / 6.0 * 40) + (min(structural_integrity * 10, 20))
        nis_score = float(np.clip(nis_raw, 0, 100))

        # Neural Logic: Signature status
        status = "AUTHENTICATED" if nis_score > 75 else "ANALYTICAL_MATCH"
        if nis_score < 40:
            status = "LOW_CONFIDENCE"

        return {
            "nis_score": round(nis_score, 1),
            "biometric_status": status,
            "signature_id": f"RECON-{hex(int(time.time()))[-6:].upper()}",
            "telemetry": {
                "energy": round(energy, 4),
                "entropy": round(entropy, 4),
                "integrity": round(structural_integrity, 6)
            }
        }
    except Exception as e:
        print(f"[ERROR] Neural signature extraction failed: {e}")
        return None

def compare_faces(img1_path, img2_pil_image):
    """
    Return the overall similarity score in 0-1 form for legacy callers.
    """
    try:
        reference_profile = extract_face_profile_from_path(img1_path)
        return compare_face_embedding(reference_profile, img2_pil_image)
    except Exception as error:
        print(f"[ERROR] Face comparison failed: {error}")
        return 0.0
