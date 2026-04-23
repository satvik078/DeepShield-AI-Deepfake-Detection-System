"""
Face Detection
==============
MTCNN (primary) with OpenCV Haarcascade fallback.
"""

import cv2
import numpy as np
from PIL import Image

# Try MTCNN, fall back to Haarcascade
_MTCNN_AVAILABLE = False
_mtcnn_detector = None

try:
    from facenet_pytorch import MTCNN
    import torch

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _mtcnn_detector = MTCNN(
        keep_all=True,
        device=_device,
        min_face_size=40,
        thresholds=[0.6, 0.7, 0.7],
    )
    _MTCNN_AVAILABLE = True
    print("✅ MTCNN face detector loaded.")
except ImportError:
    print("⚠️  facenet-pytorch not available — using Haarcascade fallback.")


def detect_faces(image: Image.Image, min_face_size: int = 40) -> list:
    """
    Detect faces in a PIL Image.

    Args:
        image: PIL Image (RGB).
        min_face_size: Minimum face size in pixels.

    Returns:
        List of dicts, each with:
            - 'face': Cropped PIL Image of the face
            - 'box': (x1, y1, x2, y2) bounding box
            - 'confidence': Detection confidence
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    if _MTCNN_AVAILABLE:
        return _detect_mtcnn(image)
    else:
        return _detect_haarcascade(image)


def _detect_mtcnn(image: Image.Image) -> list:
    """Detect faces using MTCNN."""
    boxes, probs = _mtcnn_detector.detect(image)

    results = []
    if boxes is not None:
        img_w, img_h = image.size
        for box, prob in zip(boxes, probs):
            if prob < 0.5:
                continue
            x1, y1, x2, y2 = [int(b) for b in box]
            # Clamp to image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_w, x2)
            y2 = min(img_h, y2)

            # Add margin (10%)
            margin_x = int((x2 - x1) * 0.1)
            margin_y = int((y2 - y1) * 0.1)
            x1 = max(0, x1 - margin_x)
            y1 = max(0, y1 - margin_y)
            x2 = min(img_w, x2 + margin_x)
            y2 = min(img_h, y2 + margin_y)

            face_crop = image.crop((x1, y1, x2, y2))
            results.append({
                "face": face_crop,
                "box": (x1, y1, x2, y2),
                "confidence": float(prob),
            })

    return results


def _detect_haarcascade(image: Image.Image) -> list:
    """Detect faces using OpenCV Haarcascade (fallback)."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)

    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )

    results = []
    img_h, img_w = img_array.shape[:2]
    for (x, y, w, h) in faces:
        # Add margin (10%)
        margin_x = int(w * 0.1)
        margin_y = int(h * 0.1)
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(img_w, x + w + margin_x)
        y2 = min(img_h, y + h + margin_y)

        face_crop = image.crop((x1, y1, x2, y2))
        results.append({
            "face": face_crop,
            "box": (x1, y1, x2, y2),
            "confidence": 0.9,  # Haarcascade doesn't give confidence
        })

    return results


def detect_faces_from_frame(frame: np.ndarray) -> list:
    """
    Detect faces from a BGR numpy frame (e.g., from OpenCV/webcam).

    Args:
        frame: BGR numpy array.

    Returns:
        Same format as detect_faces().
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    return detect_faces(pil_image)
