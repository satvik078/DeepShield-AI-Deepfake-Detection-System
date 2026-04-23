"""
Explainability Module
=====================
Generates human-readable explanations from Grad-CAM heatmaps
by analyzing spatial activation patterns on detected face regions.
"""

import numpy as np


# Define face region boundaries (relative to 224x224 face crop)
FACE_REGIONS = {
    "forehead": {"y_range": (0.0, 0.25), "x_range": (0.15, 0.85)},
    "left_eye": {"y_range": (0.25, 0.45), "x_range": (0.10, 0.45)},
    "right_eye": {"y_range": (0.25, 0.45), "x_range": (0.55, 0.90)},
    "nose": {"y_range": (0.35, 0.65), "x_range": (0.30, 0.70)},
    "mouth": {"y_range": (0.60, 0.85), "x_range": (0.20, 0.80)},
    "left_cheek": {"y_range": (0.40, 0.70), "x_range": (0.0, 0.25)},
    "right_cheek": {"y_range": (0.40, 0.70), "x_range": (0.75, 1.0)},
    "chin": {"y_range": (0.80, 1.0), "x_range": (0.25, 0.75)},
    "face_boundary": {"y_range": (0.0, 1.0), "x_range": (0.0, 0.10)},
}

# Explanation templates for each region
REGION_EXPLANATIONS = {
    "forehead": [
        "Texture inconsistencies detected in the forehead region",
        "Unusual skin smoothing patterns on the forehead",
    ],
    "left_eye": [
        "Abnormal artifact patterns around the left eye area",
        "Inconsistent reflection pattern in the left eye",
    ],
    "right_eye": [
        "Abnormal artifact patterns around the right eye area",
        "Inconsistent reflection pattern in the right eye",
    ],
    "nose": [
        "Geometric distortion detected around the nose bridge",
        "Unnatural shadow patterns on the nose region",
    ],
    "mouth": [
        "Lip-sync or mouth region manipulation artifacts detected",
        "Inconsistent texture blending around the mouth area",
    ],
    "left_cheek": [
        "Blending artifacts visible on the left cheek boundary",
        "Unnatural skin texture transition on the left side",
    ],
    "right_cheek": [
        "Blending artifacts visible on the right cheek boundary",
        "Unnatural skin texture transition on the right side",
    ],
    "chin": [
        "Face-swap blending seam detected near the chin/jawline",
        "Texture mismatch at the lower face boundary",
    ],
    "face_boundary": [
        "Face boundary blending artifacts detected",
        "Visible splicing seam along the face edge",
    ],
}


def analyze_heatmap(heatmap: np.ndarray, label: str, confidence: float) -> dict:
    """
    Analyze a Grad-CAM heatmap and produce human-readable explanations.

    Args:
        heatmap: Grad-CAM heatmap (H, W) in [0, 1] range.
        label: Prediction label ('REAL' or 'FAKE').
        confidence: Prediction confidence (0-100).

    Returns:
        dict with:
            - 'summary': One-line summary
            - 'details': List of region-specific explanations
            - 'activated_regions': List of region names with high activation
            - 'risk_level': 'low', 'medium', or 'high'
    """
    h, w = heatmap.shape

    # Calculate activation intensity per region
    region_activations = {}
    for region_name, bounds in FACE_REGIONS.items():
        y1 = int(bounds["y_range"][0] * h)
        y2 = int(bounds["y_range"][1] * h)
        x1 = int(bounds["x_range"][0] * w)
        x2 = int(bounds["x_range"][1] * w)

        region_patch = heatmap[y1:y2, x1:x2]
        if region_patch.size > 0:
            region_activations[region_name] = float(np.mean(region_patch))
        else:
            region_activations[region_name] = 0.0

    # Find regions with high activation (above threshold)
    threshold = 0.3
    activated = {
        k: v for k, v in region_activations.items() if v > threshold
    }
    # Sort by activation intensity
    activated = dict(sorted(activated.items(), key=lambda x: x[1], reverse=True))

    # Generate explanations
    details = []

    if label == "REAL":
        summary = f"Image appears to be authentic (confidence: {confidence:.1f}%)"
        if activated:
            details.append(
                "The model examined key facial regions and found no significant "
                "manipulation artifacts."
            )
            top_regions = list(activated.keys())[:3]
            regions_str = ", ".join(r.replace("_", " ") for r in top_regions)
            details.append(
                f"Regions analyzed: {regions_str} — all consistent with a genuine image."
            )
        risk_level = "low"

    else:  # FAKE
        # Determine risk level
        if confidence > 85:
            risk_level = "high"
        elif confidence > 65:
            risk_level = "medium"
        else:
            risk_level = "low"

        summary = (
            f"Deepfake manipulation detected (confidence: {confidence:.1f}%, "
            f"risk level: {risk_level})"
        )

        if not activated:
            details.append(
                "The model detected subtle manipulation artifacts across the face."
            )
        else:
            top_regions = list(activated.keys())[:4]
            for region_name in top_regions:
                # Pick an explanation for this region
                explanations = REGION_EXPLANATIONS.get(region_name, [])
                if explanations:
                    intensity = activated[region_name]
                    idx = 0 if intensity > 0.5 else min(1, len(explanations) - 1)
                    detail = explanations[idx]
                    detail += f" (activation: {intensity:.0%})"
                    details.append(detail)

            # Add overall assessment
            if len(top_regions) >= 3:
                details.append(
                    "Multiple facial regions show manipulation artifacts — "
                    "consistent with a face-swap or full-face synthesis deepfake."
                )
            elif "mouth" in top_regions:
                details.append(
                    "Concentrated activity around the mouth suggests possible "
                    "lip-sync manipulation (e.g., audio-driven deepfake)."
                )

    return {
        "summary": summary,
        "details": details,
        "activated_regions": list(activated.keys()),
        "region_activations": {k: round(v, 3) for k, v in region_activations.items()},
        "risk_level": risk_level,
    }
