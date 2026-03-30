from __future__ import annotations

import base64
import io
import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.services.ml_service import preprocess_image


logger = logging.getLogger("app.gradcam_service")


def generate_gradcam_keras(model: Any, image_array: np.ndarray, last_conv_layer_name: str) -> np.ndarray:
    import tensorflow as tf  # lazy import

    conv_layer = model.get_layer(last_conv_layer_name)
    grad_model = tf.keras.models.Model([model.inputs], [conv_layer.output, model.output])

    img_tensor = tf.convert_to_tensor(image_array)
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_tensor)
        if len(predictions.shape) == 2 and predictions.shape[-1] > 1:
            class_channel = tf.reduce_max(predictions, axis=1)
        else:
            class_channel = tf.squeeze(predictions)

    grads = tape.gradient(class_channel, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(tf.multiply(pooled_grads, conv_outputs), axis=-1)
    heatmap = tf.nn.relu(heatmap)

    heatmap = heatmap.numpy()
    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)
    heatmap = (heatmap * 255).astype(np.uint8)

    h, w = image_array.shape[1], image_array.shape[2]
    heatmap = cv2.resize(heatmap, (w, h))
    return heatmap


def overlay_heatmap_on_image(original_image_bytes: bytes, heatmap_array: np.ndarray) -> bytes:
    img = Image.open(io.BytesIO(original_image_bytes)).convert("RGB")
    original = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    if heatmap_array.dtype != np.uint8:
        heatmap = np.clip(heatmap_array, 0, 255).astype(np.uint8)
    else:
        heatmap = heatmap_array

    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    blended = cv2.addWeighted(original, 0.6, heatmap_colored, 0.4, 0)

    ok, buf = cv2.imencode(".jpg", blended)
    if not ok:
        raise ValueError("Failed to encode Grad-CAM overlay as JPEG")
    return buf.tobytes()


def _region_hint(heatmap: np.ndarray) -> str:
    h, w = heatmap.shape[:2]
    y, x = np.unravel_index(int(np.argmax(heatmap)), (h, w))
    horiz = "left" if x < w / 3 else "center" if x < 2 * w / 3 else "right"
    vert = "upper" if y < h / 3 else "middle" if y < 2 * h / 3 else "lower"
    return f"Abnormality detected in {vert}-{horiz} region"


def generate_gradcam_for_disease(
    disease: str,
    image_bytes: bytes,
    *,
    model: Any | None,
    model_kind: str | None,
) -> tuple[str | None, str]:
    disease_key = (disease or "").strip().lower()
    last_conv_by_disease = {
        "lung-cancer": "conv5_block3_out",
        "lung_cancer": "conv5_block3_out",
        "skin-disease": "top_conv",
        "skin_disease": "top_conv",
        "diabetic-retinopathy": "block7a_project_conv",
        "diabetic_retinopathy": "block7a_project_conv",
        "dr": "block7a_project_conv",
    }

    last_conv = last_conv_by_disease.get(disease_key)
    if not last_conv:
        return None, "Grad-CAM not available for this disease"

    if model is None or model_kind != "keras":
        # Keras-specific implementation requested; keep frontend unblocked.
        return None, "Grad-CAM unavailable (model missing or unsupported format)"

    image_array = preprocess_image(image_bytes, (224, 224))
    try:
        heatmap = generate_gradcam_keras(model, image_array, last_conv)
        overlay_bytes = overlay_heatmap_on_image(image_bytes, heatmap)
        b64 = base64.b64encode(overlay_bytes).decode("utf-8")
        return b64, _region_hint(heatmap)
    except Exception as e:
        logger.warning("Grad-CAM generation failed: %s", e)
        return None, "Grad-CAM generation failed"

