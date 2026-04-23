"""
Model Inference
===============
Load trained ViT (Vision Transformer) model and run predictions.
Uses HuggingFace transformers with safetensors format.
"""

import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor


def load_model(model_path: str):
    """
    Load a trained ViT model from a HuggingFace-format directory.

    The directory should contain:
        - config.json
        - model.safetensors
        - preprocessor_config.json

    Args:
        model_path: Path to the model directory.

    Returns:
        Tuple of (model, processor) — model in eval mode on the appropriate device.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = ViTForImageClassification.from_pretrained(
        model_path, attn_implementation="eager"
    )
    processor = ViTImageProcessor.from_pretrained(model_path)

    model.to(device)
    model.eval()

    # Store metadata on the model for convenience
    model._device = device
    model._processor = processor
    model._img_size = processor.size.get("height", 224)

    # id2label from config.json: {"0": "Fake", "1": "Real"}
    model._id2label = model.config.id2label
    model._label2id = model.config.label2id

    return model


def predict(model, image: Image.Image) -> dict:
    """
    Run deepfake prediction on a single face image.

    Args:
        model: Loaded ViT model (from load_model).
        image: PIL Image (RGB) — should be a cropped face.

    Returns:
        dict with:
            - 'label': 'REAL' or 'FAKE'
            - 'confidence': float [0, 100]
            - 'probabilities': dict with per-class probabilities
    """
    device = model._device
    processor = model._processor

    if image.mode != "RGB":
        image = image.convert("RGB")

    # Preprocess using the ViT processor (handles resize + normalize)
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)

    with torch.no_grad():
        outputs = model(pixel_values)
        logits = outputs.logits  # shape: (1, 2)
        probs = torch.softmax(logits, dim=-1).squeeze()  # shape: (2,)

    # id2label: 0 -> Fake, 1 -> Real
    fake_prob = probs[0].item()
    real_prob = probs[1].item()

    if real_prob > fake_prob:
        label = "REAL"
        confidence = real_prob
    else:
        label = "FAKE"
        confidence = fake_prob

    return {
        "label": label,
        "confidence": round(confidence * 100, 2),
        "probabilities": {
            "fake": round(fake_prob * 100, 2),
            "real": round(real_prob * 100, 2),
        },
    }


def predict_batch(model, images: list) -> list:
    """
    Run predictions on a batch of face images.

    Args:
        model: Loaded model.
        images: List of PIL Images.

    Returns:
        List of prediction dicts.
    """
    return [predict(model, img) for img in images]
