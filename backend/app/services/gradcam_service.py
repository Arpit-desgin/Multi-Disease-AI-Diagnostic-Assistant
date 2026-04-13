"""
gradcam_service.py — Grad-CAM for PyTorch ResNet models.

Uses hook-based Grad-CAM compatible with any ResNet (no architecture-specific
layer names needed — we always hook the last conv block's output).
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.services.ml_service import preprocess_image

logger = logging.getLogger("app.gradcam_service")


# ─── Hook-based Grad-CAM ─────────────────────────────────────────────────────

class _GradCAMHook:
    """Registers forward + backward hooks on a target layer."""

    def __init__(self, layer: Any) -> None:
        self.activations: Optional[np.ndarray] = None
        self.gradients:   Optional[np.ndarray] = None
        self._fwd = layer.register_forward_hook(self._save_activation)
        self._bwd = layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _module: Any, _input: Any, output: Any) -> None:
        self.activations = output.detach().cpu().numpy()   # (1, C, H, W)

    def _save_gradient(self, _module: Any, _grad_input: Any, grad_output: Any) -> None:
        self.gradients = grad_output[0].detach().cpu().numpy()  # (1, C, H, W)

    def remove(self) -> None:
        self._fwd.remove()
        self._bwd.remove()


def _find_last_conv_layer(model: Any) -> Any:
    """
    Walk the model in reverse to find the last nn.Conv2d.
    Works for any ResNet variant without knowing layer names.
    """
    import torch.nn as nn
    last = None
    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            last = module
    if last is None:
        raise ValueError("No Conv2d layer found in model")
    return last


def _compute_gradcam(
    model: Any,
    image_bytes: bytes,
    target_class: Optional[int] = None,
) -> np.ndarray:
    """
    Returns a (H, W) heatmap array (uint8, 0-255).
    If target_class is None, uses the highest-scoring class.
    """
    import torch

    # preprocess_image returns torch.Tensor, handle it properly
    tensor = preprocess_image(image_bytes)                  # (1, 3, 224, 224) float32 Tensor
    
    # Ensure it's a tensor and set requires_grad
    if isinstance(tensor, np.ndarray):
        x = torch.from_numpy(tensor).float()
    else:
        x = tensor
    
    x = x.requires_grad_(True)

    conv_layer = _find_last_conv_layer(model)
    hook       = _GradCAMHook(conv_layer)

    try:
        model.zero_grad()
        out = model(x)                                   # (1, num_classes)
        if isinstance(out, (list, tuple)):
            out = out[0]

        if target_class is None:
            target_class = int(out.argmax(dim=1).item())

        score = out[0, target_class]
        score.backward()

        acts  = hook.activations[0]   # (C, h, w) - already numpy from _save_activation
        grads = hook.gradients[0]     # (C, h, w) - already numpy from _save_gradient
        
        # Ensure both are numpy arrays (safety check)
        if isinstance(acts, torch.Tensor):
            acts = acts.detach().cpu().numpy()
        if isinstance(grads, torch.Tensor):
            grads = grads.detach().cpu().numpy()

        # Global average pool gradients → weights
        weights = grads.mean(axis=(1, 2), keepdims=True)   # (C, 1, 1)
        cam     = (weights * acts).sum(axis=0)              # (h, w)
        cam     = np.maximum(cam, 0)                        # ReLU

        # Normalise to [0, 255]
        if cam.max() > 0:
            cam = cam / cam.max()
        heatmap = (cam * 255).astype(np.uint8)

        # Resize to input resolution
        h, w = x.shape[2], x.shape[3]                      # (H, W)
        heatmap = cv2.resize(heatmap, (w, h))
        return heatmap

    finally:
        hook.remove()


def _overlay_heatmap(original_bytes: bytes, heatmap: np.ndarray, alpha: float = 0.45) -> bytes:
    """Blend JET-coloured heatmap over the original image. Returns JPEG bytes."""
    img = Image.open(io.BytesIO(original_bytes)).convert("RGB")
    orig_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    h, w = orig_bgr.shape[:2]
    heatmap_resized = cv2.resize(heatmap, (w, h))
    heatmap_colored = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)

    blended = cv2.addWeighted(orig_bgr, 1 - alpha, heatmap_colored, alpha, 0)

    ok, buf = cv2.imencode(".jpg", blended, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise ValueError("Failed to encode Grad-CAM overlay image")
    return buf.tobytes()


def _region_hint(heatmap: np.ndarray) -> str:
    h, w = heatmap.shape[:2]
    y, x = np.unravel_index(int(np.argmax(heatmap)), (h, w))
    horiz = "left" if x < w / 3 else ("center" if x < 2 * w / 3 else "right")
    vert  = "upper" if y < h / 3 else ("middle" if y < 2 * h / 3 else "lower")
    return f"Abnormality detected in {vert}-{horiz} region"


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_gradcam_for_disease(
    disease: str,
    image_bytes: bytes,
    *,
    model: Any,
    model_kind: str,
) -> Tuple[Optional[str], str]:
    """
    Generate a Grad-CAM heatmap overlay.

    Returns:
        (base64_jpeg_str | None, hint_string)
    """
    if model is None:
        return None, "Grad-CAM unavailable (model not loaded)"

    if model_kind != "torch":
        return None, "Grad-CAM only supported for PyTorch models"

    try:
        heatmap      = _compute_gradcam(model, image_bytes)
        overlay_jpeg = _overlay_heatmap(image_bytes, heatmap)
        b64          = base64.b64encode(overlay_jpeg).decode("utf-8")
        hint         = _region_hint(heatmap)
        logger.info(f"[GradCAM] ✅ Generated for disease={disease}  hint={hint}")
        return b64, hint
    except Exception as exc:
        logger.warning(f"[GradCAM] Generation failed for {disease}: {exc}", exc_info=True)
        return None, "Grad-CAM generation failed"
