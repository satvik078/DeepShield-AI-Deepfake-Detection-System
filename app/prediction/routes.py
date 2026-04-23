"""
Prediction Routes
=================
Image, video, and webcam deepfake prediction endpoints.
"""

import base64
import io
import os
import tempfile

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image

from ..extensions import db
from ..models.activity import Activity
from ..utils.face_detector import detect_faces
from ..utils.inference import predict
from ..utils.gradcam import generate_gradcam
from ..utils.explainer import analyze_heatmap
from ..utils.video_processor import process_video

prediction_bp = Blueprint("prediction", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}


def _allowed_file(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _update_usage(user_id: int):
    """Increment the user's usage counter."""
    activity = (
        Activity.query.filter_by(user_id=user_id)
        .order_by(Activity.login_time.desc())
        .first()
    )
    if activity:
        activity.increment_usage()
        db.session.commit()


def _get_model():
    """Get the loaded model or raise error."""
    model = current_app.config.get("MODEL")
    if model is None:
        return None
    return model


@prediction_bp.route("/image", methods=["POST"])
@jwt_required()
def predict_image():
    """
    Upload an image for deepfake prediction.

    Expects: multipart form-data with 'file' field.
    Returns: prediction result with Grad-CAM heatmap and explanation.
    """
    model = _get_model()
    if model is None:
        return jsonify({"error": "Model not loaded. Please ensure models/vit-deepfake directory exists with model files."}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not _allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"}), 400

    try:
        # Read image
        image = Image.open(file.stream).convert("RGB")

        # Detect faces
        faces = detect_faces(image)

        if not faces:
            return jsonify({
                "error": "No face detected in the image. Please upload an image with a clearly visible face.",
                "faces_found": 0,
            }), 400

        # Use the largest face
        largest_face = max(faces, key=lambda f: (
            (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])
        ))
        face_image = largest_face["face"]

        # Predict
        prediction = predict(model, face_image)

        # Generate Grad-CAM
        gradcam_result = generate_gradcam(model, face_image)

        # Generate explanation
        explanation = analyze_heatmap(
            gradcam_result["raw_heatmap"],
            prediction["label"],
            prediction["confidence"],
        )

        # Update usage
        user_id = get_jwt_identity()
        _update_usage(int(user_id))

        return jsonify({
            "prediction": prediction,
            "heatmap": gradcam_result["heatmap_base64"],
            "explanation": explanation,
            "faces_found": len(faces),
            "face_box": largest_face["box"],
            "face_confidence": largest_face["confidence"],
        }), 200

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@prediction_bp.route("/video", methods=["POST"])
@jwt_required()
def predict_video():
    """
    Upload a video for deepfake prediction.

    Expects: multipart form-data with 'file' field.
    Returns: aggregate prediction with per-frame details.
    """
    model = _get_model()
    if model is None:
        return jsonify({"error": "Model not loaded. Please ensure models/vit-deepfake directory exists with model files."}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not _allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"}), 400

    try:
        # Save video temporarily
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.rsplit(".", 1)[1].lower()
        with tempfile.NamedTemporaryFile(
            suffix=f".{ext}", dir=upload_dir, delete=False
        ) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Process video
            result = process_video(
                model=model,
                video_path=tmp_path,
                face_detector_fn=detect_faces,
                predict_fn=predict,
                fps=1,
            )

            # Update usage
            user_id = get_jwt_identity()
            _update_usage(int(user_id))

            return jsonify(result), 200

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return jsonify({"error": f"Video processing failed: {str(e)}"}), 500


@prediction_bp.route("/webcam", methods=["POST"])
@jwt_required()
def predict_webcam():
    """
    Process a single webcam frame for real-time detection.

    Expects: JSON with 'frame' field containing base64-encoded image.
    Returns: prediction result (lightweight — no Grad-CAM for speed).
    """
    model = _get_model()
    if model is None:
        return jsonify({"error": "Model not loaded."}), 503

    data = request.get_json()
    if not data or "frame" not in data:
        return jsonify({"error": "No frame data. Send JSON with 'frame' (base64)."}), 400

    try:
        # Decode base64 frame
        frame_data = data["frame"]
        # Handle data URL format (data:image/...;base64,...)
        if "," in frame_data:
            frame_data = frame_data.split(",", 1)[1]

        image_bytes = base64.b64decode(frame_data)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Detect faces
        faces = detect_faces(image)

        if not faces:
            return jsonify({
                "prediction": {"label": "NO FACE", "confidence": 0},
                "faces_found": 0,
            }), 200

        # Use largest face
        largest_face = max(faces, key=lambda f: (
            (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])
        ))
        prediction = predict(model, largest_face["face"])

        return jsonify({
            "prediction": prediction,
            "faces_found": len(faces),
            "face_box": largest_face["box"],
        }), 200

    except Exception as e:
        return jsonify({"error": f"Webcam prediction failed: {str(e)}"}), 500
