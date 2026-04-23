"""
Image Preprocessing
===================
Transforms for inference — matches ViT model preprocessing.
Uses [0.5, 0.5, 0.5] normalization as specified in preprocessor_config.json.
"""

import numpy as np
import torch
from PIL import Image
from torchvision import transforms


# ViT normalization (from preprocessor_config.json)
VIT_MEAN = [0.5, 0.5, 0.5]
VIT_STD = [0.5, 0.5, 0.5]
IMG_SIZE = 224


def get_inference_transform(img_size: int = IMG_SIZE) -> transforms.Compose:
    """Return the standard inference transform pipeline for ViT."""
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=VIT_MEAN, std=VIT_STD),
    ])


def preprocess_image(image: Image.Image, img_size: int = IMG_SIZE) -> torch.Tensor:
    """
    Preprocess a PIL Image for model inference.

    Args:
        image: PIL Image (RGB).
        img_size: Target size.

    Returns:
        Tensor of shape (1, 3, img_size, img_size).
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    transform = get_inference_transform(img_size)
    tensor = transform(image)
    return tensor.unsqueeze(0)  # Add batch dim


def preprocess_batch(images: list, img_size: int = IMG_SIZE) -> torch.Tensor:
    """
    Preprocess a list of PIL Images into a batch tensor.

    Args:
        images: List of PIL Images (RGB).
        img_size: Target size.

    Returns:
        Tensor of shape (N, 3, img_size, img_size).
    """
    transform = get_inference_transform(img_size)
    tensors = []
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        tensors.append(transform(img))
    return torch.stack(tensors)


def denormalize(tensor: torch.Tensor) -> np.ndarray:
    """
    Reverse ViT normalization for visualization.

    Args:
        tensor: Normalized tensor (C, H, W).

    Returns:
        Numpy array (H, W, C) in [0, 255] uint8.
    """
    mean = torch.tensor(VIT_MEAN).view(3, 1, 1)
    std = torch.tensor(VIT_STD).view(3, 1, 1)
    tensor = tensor.cpu().clone()
    tensor = tensor * std + mean
    tensor = torch.clamp(tensor, 0, 1)
    return (tensor.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
