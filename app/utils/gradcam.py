"""
Attention-Based Explainability for ViT
=======================================
Generates visual explanations for ViT model predictions using
attention rollout — the standard explainability technique for
Vision Transformers (which have no convolutional layers).
"""

import base64
import io

import cv2
import numpy as np
import torch
from PIL import Image

from .preprocessing import preprocess_image


class ViTAttentionRollout:
    """
    Attention Rollout for Vision Transformer models.
    Aggregates attention across all layers to produce a spatial heatmap
    showing which image regions the model focused on.
    """

    def __init__(self, model):
        self.model = model
        self.device = model._device

    def generate(self, image: Image.Image, img_size: int = 224) -> np.ndarray:
        """
        Generate attention rollout heatmap for a face image.

        Args:
            image: PIL Image (RGB).
            img_size: Model input size.

        Returns:
            Heatmap as numpy array (H, W) in [0, 1] range.
        """
        self.model.eval()
        processor = self.model._processor

        if image.mode != "RGB":
            image = image.convert("RGB")

        inputs = processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)

        with torch.no_grad():
            outputs = self.model(pixel_values, output_attentions=True)
            attentions = outputs.attentions  # tuple of (batch, heads, seq, seq)

        # Fallback if attentions are not available
        if not attentions:
            return np.ones((img_size, img_size), dtype=np.float32) * 0.5

        # Attention rollout
        result = torch.eye(attentions[0].size(-1)).to(self.device)

        for attention in attentions:
            # Average across heads
            attention_heads_fused = attention.mean(dim=1)  # (batch, seq, seq)
            attention_heads_fused = attention_heads_fused.squeeze(0)  # (seq, seq)

            # Add identity (residual connection)
            I = torch.eye(attention_heads_fused.size(-1)).to(self.device)
            a = (attention_heads_fused + I) / 2

            # Normalize rows
            a = a / a.sum(dim=-1, keepdim=True)

            result = torch.matmul(a, result)

        # Get the attention from CLS token to all patches
        # CLS token is at index 0
        mask = result[0, 1:]  # skip CLS token itself

        # Reshape to 2D grid
        # ViT with patch_size=16 and image_size=224 → 14x14 patches
        num_patches = int(mask.size(0) ** 0.5)
        if num_patches * num_patches != mask.size(0):
            # Handle non-square cases
            num_patches = int(np.ceil(mask.size(0) ** 0.5))

        mask = mask[:num_patches * num_patches]
        mask = mask.reshape(num_patches, num_patches).cpu().numpy()

        # Normalize to [0, 1]
        mask = (mask - mask.min()) / (mask.max() - mask.min() + 1e-8)

        # Resize to image size
        mask = cv2.resize(mask, (img_size, img_size))

        return mask

    def cleanup(self):
        """No-op for compatibility. Attention rollout doesn't use hooks."""
        pass


def generate_heatmap_overlay(
    original_image: Image.Image,
    heatmap: np.ndarray,
    alpha: float = 0.5,
    colormap: int = cv2.COLORMAP_JET,
) -> Image.Image:
    """
    Overlay attention heatmap on the original image.

    Args:
        original_image: Original PIL Image.
        heatmap: Attention heatmap (H, W) in [0, 1].
        alpha: Overlay transparency.
        colormap: OpenCV colormap.

    Returns:
        PIL Image with heatmap overlay.
    """
    img = np.array(original_image.resize((224, 224)))

    # Convert heatmap to colormap
    heatmap_uint8 = np.uint8(255 * heatmap)
    heatmap_colored = cv2.applyColorMap(heatmap_uint8, colormap)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    # Blend
    overlay = np.uint8(alpha * heatmap_colored + (1 - alpha) * img)

    return Image.fromarray(overlay)


def heatmap_to_base64(overlay_image: Image.Image) -> str:
    """Convert PIL Image to base64-encoded PNG string."""
    buffer = io.BytesIO()
    overlay_image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def generate_gradcam(model, image: Image.Image) -> dict:
    """
    Full explainability pipeline: generate attention heatmap + overlay + base64.

    Uses attention rollout (ViT-native) instead of Grad-CAM (CNN-only).

    Args:
        model: Loaded ViT model.
        image: PIL Image (cropped face).

    Returns:
        dict with 'heatmap_base64' and 'raw_heatmap'.
    """
    rollout = ViTAttentionRollout(model)
    try:
        heatmap = rollout.generate(image)
        overlay = generate_heatmap_overlay(image, heatmap)
        b64 = heatmap_to_base64(overlay)
        return {
            "heatmap_base64": b64,
            "raw_heatmap": heatmap,
        }
    finally:
        rollout.cleanup()
