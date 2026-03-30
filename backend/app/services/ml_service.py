from __future__ import annotations

import io
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
from PIL import Image

from app.config import settings


logger = logging.getLogger("app.ml_service")


@dataclass
class _LoadedModel:
    kind: str  # "keras" | "torch"
    model: Any


_model_lock = threading.Lock()
_models: dict[str, _LoadedModel] = {}
_model_paths = {
    "lung_cancer": settings.LUNG_MODEL_PATH,
    "skin_disease": settings.SKIN_MODEL_PATH,
    "diabetic_retinopathy": settings.DR_MODEL_PATH,
}


def _load_keras_model(path: str) -> Any:
    from tensorflow.keras.models import load_model  # lazy import

    return load_model(path)


def _load_torch_model(path: str) -> Any:
    import torch  # lazy import

    obj = torch.load(path, map_location="cpu")
    model = obj["model"] if isinstance(obj, dict) and "model" in obj else obj
    if hasattr(model, "eval"):
        model.eval()
    return model


def _get_or_load_model(path: str) -> _LoadedModel | None:
    with _model_lock:
        if path in _models:
            return _models[path]

        if not path or not os.path.exists(path):
            logger.warning("Model not found at %s, using mock predictions", path)
            return None

        ext = os.path.splitext(path)[1].lower()
        if ext == ".h5":
            loaded = _LoadedModel(kind="keras", model=_load_keras_model(path))
        elif ext == ".pt":
            loaded = _LoadedModel(kind="torch", model=_load_torch_model(path))
        else:
            logger.warning("Unsupported model format at %s, using mock predictions", path)
            return None

        _models[path] = loaded
        return loaded


def get_loaded_model_for_disease(disease: str) -> tuple[Any | None, str | None]:
    """
    Returns (model, model_kind) for Grad-CAM usage.
    model_kind is "keras" | "torch" or None when missing.
    """
    key = (disease or "").strip().lower().replace("-", "_")
    path = _model_paths.get(key)
    if not path:
        return None, None

    loaded = _get_or_load_model(path)
    if loaded is None:
        return None, None
    return loaded.model, loaded.kind


def get_model_status() -> Dict[str, Dict[str, Any]]:
    status: Dict[str, Dict[str, Any]] = {}
    for name, path in _model_paths.items():
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        loaded = path in _models
        status[name] = {"path": path, "exists": exists, "size_bytes": size, "loaded": loaded}
    return status


def preprocess_image(image_bytes: bytes, target_size: tuple[int, int], normalize: bool = True) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img, dtype=np.float32)
    if normalize:
        arr = arr / 255.0
    arr = np.expand_dims(arr, axis=0)  # (1, H, W, C)
    return arr


def _keras_predict(loaded: _LoadedModel, batch: np.ndarray) -> np.ndarray:
    preds = loaded.model.predict(batch, verbose=0)
    return np.asarray(preds)


def _torch_predict(loaded: _LoadedModel, batch: np.ndarray) -> np.ndarray:
    import torch  # lazy import

    x = torch.from_numpy(batch).permute(0, 3, 1, 2).float()  # NCHW
    with torch.no_grad():
        out = loaded.model(x)
    if isinstance(out, (list, tuple)):
        out = out[0]
    return out.detach().cpu().numpy()


def _predict_raw(loaded: _LoadedModel, batch: np.ndarray) -> np.ndarray:
    if loaded.kind == "keras":
        return _keras_predict(loaded, batch)
    return _torch_predict(loaded, batch)


def _as_binary_probs(raw: np.ndarray) -> tuple[float, float]:
    """
    Returns (p_normal, p_positive) in [0,1].
    Supports: shape (1,1) sigmoid, (1,2) softmax/logits, or flat.
    """
    x = np.squeeze(raw)
    if x.ndim == 0:
        p_pos = float(1.0 / (1.0 + np.exp(-x)))
        return 1.0 - p_pos, p_pos

    x = np.array(x, dtype=np.float32).reshape(-1)
    if x.size == 1:
        p_pos = float(np.clip(x[0], 0.0, 1.0))
        return 1.0 - p_pos, p_pos

    if x.size >= 2:
        logits = x[:2]
        exps = np.exp(logits - np.max(logits))
        probs = exps / np.sum(exps)
        return float(probs[0]), float(probs[1])

    return 0.5, 0.5


def predict_lung_cancer(image_bytes: bytes) -> dict:
    path = settings.LUNG_MODEL_PATH
    loaded = _get_or_load_model(path)

    if loaded is None:
        return {
            "mock": True,
            "prediction": "Normal",
            "confidence": 71.0,
            "risk_level": "LOW",
            "class_probabilities": {"normal": 0.71, "cancer": 0.29},
        }

    batch = preprocess_image(image_bytes, (224, 224))
    raw = _predict_raw(loaded, batch)
    p_normal, p_cancer = _as_binary_probs(raw)
    prediction = "Lung Cancer Detected" if p_cancer >= 0.5 else "Normal"
    confidence = float(max(p_normal, p_cancer) * 100.0)
    return {
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "risk_level": "HIGH" if prediction == "Lung Cancer Detected" else "LOW",
        "class_probabilities": {"normal": round(p_normal, 4), "cancer": round(p_cancer, 4)},
    }


def predict_skin_disease(image_bytes: bytes) -> dict:
    path = settings.SKIN_MODEL_PATH
    loaded = _get_or_load_model(path)

    if loaded is None:
        stage1 = {"label": "Benign", "confidence": 76.0}
        stage2 = {"label": "Nevus", "confidence": 61.0}
        return {
            "mock": True,
            "stage1_result": stage1,
            "stage2_result": stage2,
            "confidence": stage1["confidence"],
            "class_probabilities": {"benign": 0.76, "malignant": 0.24},
        }

    batch = preprocess_image(image_bytes, (224, 224))
    raw = _predict_raw(loaded, batch)
    p_benign, p_malignant = _as_binary_probs(raw)
    stage1_label = "Malignant" if p_malignant >= 0.5 else "Benign"
    stage1_conf = float(max(p_benign, p_malignant) * 100.0)

    # Single-file model support: if your real pipeline uses a second model,
    # wire it here later; for now we return a conservative placeholder.
    stage2 = None
    if stage1_label == "Malignant":
        stage2 = {"label": "Melanoma / Basal Cell / SCC", "confidence": round(stage1_conf * 0.85, 2)}
    else:
        stage2 = {"label": "Benign subtype", "confidence": round(stage1_conf * 0.85, 2)}

    return {
        "stage1_result": {"label": stage1_label, "confidence": round(stage1_conf, 2)},
        "stage2_result": stage2,
        "confidence": round(stage1_conf, 2),
        "class_probabilities": {"benign": round(p_benign, 4), "malignant": round(p_malignant, 4)},
    }


def predict_diabetic_retinopathy(image_bytes: bytes) -> dict:
    path = settings.DR_MODEL_PATH
    loaded = _get_or_load_model(path)

    if loaded is None:
        stage1 = {"label": "No DR", "confidence": 73.0}
        stage2 = None
        return {
            "mock": True,
            "stage1_result": stage1,
            "stage2_result": stage2,
            "confidence": stage1["confidence"],
            "class_probabilities": {"no_dr": 0.73, "dr": 0.27},
        }

    batch = preprocess_image(image_bytes, (224, 224))
    raw = _predict_raw(loaded, batch)
    p_no, p_yes = _as_binary_probs(raw)
    has_dr = p_yes >= 0.5
    stage1_label = "DR" if has_dr else "No DR"
    stage1_conf = float(max(p_no, p_yes) * 100.0)

    stage2 = None
    if has_dr:
        stage2 = {"label": "Mild / Moderate / Severe / Proliferative", "confidence": round(stage1_conf * 0.85, 2)}

    return {
        "stage1_result": {"label": stage1_label, "confidence": round(stage1_conf, 2)},
        "stage2_result": stage2,
        "confidence": round(stage1_conf, 2),
        "class_probabilities": {"no_dr": round(p_no, 4), "dr": round(p_yes, 4)},
    }

