import argparse
import itertools
import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from face_compare import (
    cosine_similarity,
    extract_face_profile,
    extract_face_profile_from_path,
)

PROFILE_PATH = Path("assets/profiles.json")
OUTPUT_PATH = Path("models/thresholds.json")
IMAGE_DIR = Path("assets/sample_images")


def load_identity_profiles(profile_path: Path):
    if not profile_path.exists():
        return []
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"Failed to read {profile_path}: {error}")
        return []
    identities = payload.get("identities", []) if isinstance(payload, dict) else []
    return [item for item in identities if isinstance(item, dict)]


def collect_embeddings(identities):
    collected = {}
    skipped = []
    for identity in identities:
        name = str(identity.get("name", "")).strip() or "Unknown"
        image_names = identity.get("images", [])
        if not isinstance(image_names, list):
            continue

        vectors = []
        for image_name in image_names:
            image_path = IMAGE_DIR / str(image_name)
            if not image_path.exists():
                skipped.append({"identity": name, "image": str(image_name), "reason": "missing"})
                continue

            profile = extract_face_profile_from_path(str(image_path))
            embedding = profile.get("embedding")
            if embedding is None:
                skipped.append({"identity": name, "image": str(image_name), "reason": "no_face"})
                continue
            vectors.append((str(image_path), embedding))

        if vectors:
            collected[name] = vectors

    return collected, skipped


def build_synthetic_variants(image_path: Path):
    variants = []
    try:
        with Image.open(image_path) as image:
            base = image.convert("RGB")
            variants.append(("flip", ImageOps.mirror(base)))
            variants.append(("bright", ImageEnhance.Brightness(base).enhance(1.1)))
            variants.append(("contrast", ImageEnhance.Contrast(base).enhance(1.1)))
    except Exception as error:
        print(f"Failed to build synthetic variants for {image_path}: {error}")
    return variants


def build_synthetic_genuine_pairs(embeddings_by_identity):
    synthetic_pairs = []
    for identity, vectors in embeddings_by_identity.items():
        if len(vectors) != 1:
            continue

        image_path_str, base_embedding = vectors[0]
        image_path = Path(image_path_str)
        if not image_path.exists():
            continue

        for tag, variant in build_synthetic_variants(image_path):
            variant_profile = extract_face_profile(variant)
            variant_embedding = variant_profile.get("embedding")
            if variant_embedding is None:
                continue
            similarity = cosine_similarity(base_embedding, variant_embedding)
            if similarity is None:
                continue
            synthetic_pairs.append({
                "identity": identity,
                "pair": [image_path_str, f"{image_path_str}::{tag}"],
                "similarity": float(similarity),
                "synthetic": True,
            })

    return synthetic_pairs


def build_similarity_sets(embeddings_by_identity):
    genuine_scores = []
    impostor_scores = []

    for identity, vectors in embeddings_by_identity.items():
        for (path_a, emb_a), (path_b, emb_b) in itertools.combinations(vectors, 2):
            similarity = cosine_similarity(emb_a, emb_b)
            if similarity is not None:
                genuine_scores.append({
                    "identity": identity,
                    "pair": [path_a, path_b],
                    "similarity": float(similarity),
                })

    identity_names = list(embeddings_by_identity.keys())
    for idx, left_identity in enumerate(identity_names):
        for right_identity in identity_names[idx + 1:]:
            for path_a, emb_a in embeddings_by_identity[left_identity]:
                for path_b, emb_b in embeddings_by_identity[right_identity]:
                    similarity = cosine_similarity(emb_a, emb_b)
                    if similarity is not None:
                        impostor_scores.append({
                            "left_identity": left_identity,
                            "right_identity": right_identity,
                            "pair": [path_a, path_b],
                            "similarity": float(similarity),
                        })

    return genuine_scores, impostor_scores


def evaluate_threshold(genuine_scores, impostor_scores, threshold):
    tp = sum(1 for item in genuine_scores if item["similarity"] >= threshold)
    fn = len(genuine_scores) - tp
    fp = sum(1 for item in impostor_scores if item["similarity"] >= threshold)
    tn = len(impostor_scores) - fp

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0

    return {
        "threshold": round(float(threshold), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "accuracy": round(float(accuracy), 4),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }


def find_best_threshold(genuine_scores, impostor_scores, min_threshold=0.30, max_threshold=0.90, step=0.01):
    candidates = []
    threshold = min_threshold
    while threshold <= max_threshold + 1e-9:
        candidates.append(evaluate_threshold(genuine_scores, impostor_scores, threshold))
        threshold += step

    if not candidates:
        return None, []

    best = sorted(
        candidates,
        key=lambda item: (item["f1"], item["accuracy"], item["precision"]),
        reverse=True,
    )[0]
    return best, candidates


def main():
    parser = argparse.ArgumentParser(description="Calibrate face-match threshold from local identity profiles.")
    parser.add_argument("--profile", default=str(PROFILE_PATH), help="Path to identity profile JSON")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output path for threshold JSON")
    parser.add_argument("--min-threshold", type=float, default=0.30)
    parser.add_argument("--max-threshold", type=float, default=0.90)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument(
        "--allow-synthetic-genuine",
        action="store_true",
        help="Generate fallback genuine pairs from single-image identities via light augmentations.",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    output_path = Path(args.output)

    identities = load_identity_profiles(profile_path)
    if not identities:
        print("No identities found; aborting calibration.")
        return

    embeddings_by_identity, skipped = collect_embeddings(identities)
    genuine_scores, impostor_scores = build_similarity_sets(embeddings_by_identity)

    synthetic_pairs = []
    if args.allow_synthetic_genuine and not genuine_scores:
        synthetic_pairs = build_synthetic_genuine_pairs(embeddings_by_identity)
        genuine_scores.extend(synthetic_pairs)
        if synthetic_pairs:
            print(
                f"Added {len(synthetic_pairs)} synthetic genuine pairs from single-image identities."
            )

    if not genuine_scores or not impostor_scores:
        print("Insufficient pair data for calibration.")
        print(f"Genuine pairs: {len(genuine_scores)} | Impostor pairs: {len(impostor_scores)}")
        return

    low_sample_warning = None
    if len(genuine_scores) < 10 or len(impostor_scores) < 20:
        low_sample_warning = (
            "Low sample volume detected. Threshold quality is provisional; add more labeled images."
        )
        print(low_sample_warning)

    best, all_metrics = find_best_threshold(
        genuine_scores=genuine_scores,
        impostor_scores=impostor_scores,
        min_threshold=args.min_threshold,
        max_threshold=args.max_threshold,
        step=args.step,
    )

    payload = {
        "best_threshold": best["threshold"],
        "best_metrics": best,
        "samples": {
            "genuine_pairs": len(genuine_scores),
            "impostor_pairs": len(impostor_scores),
            "identities_used": len(embeddings_by_identity),
            "skipped_images": skipped,
            "synthetic_genuine_pairs": len(synthetic_pairs),
        },
        "warnings": [low_sample_warning] if low_sample_warning else [],
        "candidate_metrics": all_metrics,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Calibration complete. Best threshold: {best['threshold']}")
    print(f"Metrics: F1={best['f1']}, Precision={best['precision']}, Recall={best['recall']}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
