"""
Video Processing
================
Frame extraction and batch prediction for video deepfake detection.
"""

import os
import tempfile

import cv2
import numpy as np
from PIL import Image


def extract_frames(video_path: str, fps: int = 1, max_frames: int = 60) -> list:
    """
    Extract frames from a video at a specified rate.

    Args:
        video_path: Path to the video file.
        fps: Frames per second to extract (1 = one frame per second).
        max_frames: Maximum number of frames to extract.

    Returns:
        List of PIL Images (RGB).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps if video_fps > 0 else 0

    # Calculate frame interval
    frame_interval = max(1, int(video_fps / fps))

    frames = []
    frame_idx = 0

    while cap.isOpened() and len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            frames.append(pil_img)

        frame_idx += 1

    cap.release()

    return frames


def get_video_info(video_path: str) -> dict:
    """Get basic video metadata."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video"}

    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    info["duration"] = (
        info["total_frames"] / info["fps"] if info["fps"] > 0 else 0
    )
    cap.release()
    return info


def majority_vote(predictions: list) -> dict:
    """
    Aggregate per-frame predictions via majority vote.

    Args:
        predictions: List of prediction dicts with 'label' and 'confidence'.

    Returns:
        Aggregated result dict.
    """
    if not predictions:
        return {
            "label": "UNKNOWN",
            "confidence": 0.0,
            "total_frames": 0,
            "fake_frames": 0,
            "real_frames": 0,
        }

    fake_count = sum(1 for p in predictions if p["label"] == "FAKE")
    real_count = len(predictions) - fake_count

    # Average confidence across all predictions
    avg_confidence = np.mean([p["confidence"] for p in predictions])

    # Majority determines final label
    if fake_count > real_count:
        label = "FAKE"
        # Weight confidence by proportion of fake frames
        confidence = avg_confidence * (fake_count / len(predictions))
    else:
        label = "REAL"
        confidence = avg_confidence * (real_count / len(predictions))

    return {
        "label": label,
        "confidence": round(float(confidence), 2),
        "total_frames": len(predictions),
        "fake_frames": fake_count,
        "real_frames": real_count,
        "fake_ratio": round(fake_count / len(predictions) * 100, 1),
    }


def process_video(model, video_path: str, face_detector_fn, predict_fn, fps: int = 1) -> dict:
    """
    Full video processing pipeline.

    Args:
        model: Loaded ML model.
        video_path: Path to video file.
        face_detector_fn: Function to detect faces in an image.
        predict_fn: Function to predict on a face image.
        fps: Frame extraction rate.

    Returns:
        dict with overall result and per-frame details.
    """
    # Extract frames
    frames = extract_frames(video_path, fps=fps)
    video_info = get_video_info(video_path)

    frame_results = []

    for i, frame in enumerate(frames):
        # Detect faces in frame
        faces = face_detector_fn(frame)

        if faces:
            # Use the largest face (most prominent)
            largest_face = max(faces, key=lambda f: (
                (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])
            ))
            prediction = predict_fn(model, largest_face["face"])
            prediction["frame_index"] = i
            prediction["face_detected"] = True
            frame_results.append(prediction)
        else:
            frame_results.append({
                "frame_index": i,
                "face_detected": False,
                "label": "UNKNOWN",
                "confidence": 0.0,
            })

    # Filter out frames where no face was detected for voting
    valid_predictions = [r for r in frame_results if r["face_detected"]]
    aggregate = majority_vote(valid_predictions)

    return {
        "aggregate": aggregate,
        "frame_results": frame_results,
        "video_info": video_info,
        "frames_analyzed": len(frames),
        "faces_detected": len(valid_predictions),
    }
