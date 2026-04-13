import io
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
from PIL import Image

logger = logging.getLogger("app.ml_service")

# --- Constants & Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml_models"

DR_DIR = MODEL_DIR / "diabetic_retinopathy"
LUNG_DIR = MODEL_DIR / "lung"
SKIN_DIR = MODEL_DIR / "skin"

MODEL_PATHS = {
    "dr_stage1": DR_DIR / "stage1_resnet50_dr.pth",
    "dr_stage2": DR_DIR / "stage2_resnet50_severity.pth",
    "lung": LUNG_DIR / "best_model_resnet101_colab.pth",
    "skin_stage1": SKIN_DIR / "stage1_resnet101_best.pth",
    "skin_benign": SKIN_DIR / "stage2_benign_resnet101_best.pth",
    "skin_malignant": SKIN_DIR / "stage2_malignant_resnet101_best.pth",
}

# --- Labels ---
DR_STAGE1_LABELS = ["No DR", "DR"]
DR_STAGE2_LABELS = ["No DR", "Mild", "Moderate", "Severe", "Proliferative DR"]
LUNG_LABELS = ["Normal", "Lung Cancer Detected"]
SKIN_STAGE1_LABELS = ["Benign", "Malignant"]
SKIN_BENIGN_LABELS = ["Dermatofibroma", "Melanocytic nevi", "Seborrheic keratosis", "Vascular lesions"]
SKIN_MALIGNANT_LABELS = ["Basal cell carcinoma", "Melanoma", "Squamous cell carcinoma"]

# --- Global Cache (Singleton) ---
_model_cache: Dict[str, nn.Module] = {}
_cache_lock = threading.Lock()

# --- Model Building ---

def _build_resnet_model(arch: str, num_classes: int) -> nn.Module:
    """Explicitly builds ResNet architecture and replaces the FC layer."""
    if arch == "resnet50":
        model = models.resnet50(weights=None)
    elif arch == "resnet101":
        model = models.resnet101(weights=None)
    else:
        raise ValueError(f"Unsupported architecture: {arch}")
    
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model

def load_model_from_checkpoint(key: str) -> nn.Module:
    """Loads a PyTorch model by building architecture and loading model_state_dict."""
    path = MODEL_PATHS.get(key)
    if not path or not path.exists():
        raise FileNotFoundError(f"CRITICAL: Model file missing for '{key}' at: {path}")

    config = {
        "dr_stage1": "resnet50",
        "dr_stage2": "resnet50",
        "lung": "resnet101",
        "skin_stage1": "resnet101",
        "skin_benign": "resnet101",
        "skin_malignant": "resnet101",
    }

    if key not in config:
        raise ValueError(f"Unknown model key: {key}")

    arch = config[key]
    logger.info(f"[ML] Loading {key} | Arch: {arch}")
    
    # 1. Build base architecture
    if arch == "resnet50":
        model = models.resnet50(weights=None)
    elif arch == "resnet101":
        model = models.resnet101(weights=None)
    else:
        raise ValueError(f"Unsupported architecture: {arch}")

    # 2. Load checkpoint
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        checkpoint = torch.load(path, map_location="cpu")
    
    # 3. Extract state_dict
    if isinstance(checkpoint, dict):
        state_dict = checkpoint.get("model_state_dict", 
                                   checkpoint.get("state_dict", 
                                                 checkpoint.get("model", checkpoint)))
    else:
        state_dict = checkpoint

    # 4. Detect architecture type from checkpoint keys
    has_fc = any(k.startswith("fc.") for k in state_dict.keys())
    has_classifier = any(k.startswith("classifier.") for k in state_dict.keys())
    has_backbone = any(k.startswith("backbone.") for k in state_dict.keys())
    
    logger.debug(f"[ML] Checkpoint structure - fc: {has_fc}, classifier: {has_classifier}, backbone: {has_backbone}")

    # 5. Dynamically infer num_classes from checkpoint
    num_classes = None
    
    if has_classifier:
        # Look for classifier.*.weight keys, find the last one
        classifier_keys = [k for k in state_dict.keys() if k.startswith("classifier.") and k.endswith(".weight")]
        if classifier_keys:
            last_key = sorted(classifier_keys, key=lambda x: int(x.split(".")[1]))[-1]
            num_classes = state_dict[last_key].shape[0]
            logger.info(f"[ML] Inferred num_classes={num_classes} from classifier {last_key} shape {state_dict[last_key].shape}")
    elif has_fc:
        # Look for fc.*.weight keys
        fc_output_keys = ["fc.4.weight", "fc.weight", "fc.1.weight"]
        for key_name in fc_output_keys:
            if key_name in state_dict:
                num_classes = state_dict[key_name].shape[0]
                logger.info(f"[ML] Inferred num_classes={num_classes} from {key_name} shape {state_dict[key_name].shape}")
                break
    
    if num_classes is None:
        logger.error(f"[ML] Could not infer num_classes from checkpoint keys: {list(state_dict.keys())[:20]}")
        raise ValueError(f"Could not infer num_classes from checkpoint for {key}")

    logger.info(f"[ML] Detected {num_classes} classes")

    # 6. Rebuild model head based on architecture
    in_features = model.fc.in_features
    
    if has_classifier and has_backbone:
        # Custom architecture with backbone + classifier
        logger.info(f"[ML] Detected custom backbone+classifier architecture")
        
        # Extract parts of state_dict
        backbone_dict = {k.replace("backbone.", ""): v for k, v in state_dict.items() if k.startswith("backbone.")}
        classifier_dict = {k.replace("classifier.", ""): v for k, v in state_dict.items() if k.startswith("classifier.")}
        
        # Try to load backbone
        try:
            incompatible = model.load_state_dict(backbone_dict, strict=False)
            if incompatible.missing_keys:
                logger.debug(f"[ML] Backbone missing keys: {incompatible.missing_keys[:5]}")
            if incompatible.unexpected_keys:
                logger.debug(f"[ML] Backbone unexpected keys: {incompatible.unexpected_keys[:5]}")
        except RuntimeError as e:
            logger.warning(f"[ML] Backbone loading issue: {str(e)}")
        
        # Build classifier from extracted weights
        classifier_layers = []
        layer_indices = set()
        
        # Extract layer indices from classifier_dict
        for k in classifier_dict.keys():
            if "." in k:
                idx = k.split(".")[0]
                if idx.isdigit():
                    layer_indices.add(int(idx))
        
        layer_indices = sorted(layer_indices)
        logger.debug(f"[ML] Classifier layer indices: {layer_indices}")
        
        # Reconstruct layers from indices
        for idx in layer_indices:
            weight_key = f"{idx}.weight"
            bias_key = f"{idx}.bias"
            
            if weight_key in classifier_dict:
                w = classifier_dict[weight_key]
                in_f = w.shape[1] if w.ndim >= 2 else w.shape[0]
                out_f = w.shape[0]
                linear = nn.Linear(in_f, out_f)
                classifier_layers.append(linear)
                logger.debug(f"[ML] Built Linear layer {idx}: {in_f} -> {out_f}")
        
        if classifier_layers:
            model.fc = nn.Sequential(*classifier_layers)
            logger.info(f"[ML] Built classifier Sequential with {len(classifier_layers)} Linear layers")
        else:
            # Fallback: use simple Linear
            model.fc = nn.Linear(in_features, num_classes)
            logger.info(f"[ML] Fallback: using Linear for classifier")
    elif has_fc:
        # Standard ResNet fc layers
        fc_keys = [k for k in state_dict.keys() if k.startswith("fc.")]
        fc_indices = set()
        for k in fc_keys:
            if k.endswith(".weight") or k.endswith(".bias"):
                parts = k.split(".")
                if len(parts) >= 2 and parts[1].isdigit():
                    fc_indices.add(int(parts[1]))
        
        logger.debug(f"[ML] FC indices with parameters: {sorted(fc_indices)}")
        
        if fc_indices:
            max_idx = max(fc_indices)
            if max_idx >= 4:
                # Multi-layer Sequential
                model.fc = nn.Sequential(
                    nn.Identity(),                  # Index 0
                    nn.Linear(in_features, 512),    # Index 1
                    nn.ReLU(),                      # Index 2
                    nn.Dropout(0.5),                # Index 3
                    nn.Linear(512, num_classes)     # Index 4
                )
                logger.info(f"[ML] Detected Sequential fc (5 layers) with {num_classes} classes")
            elif max_idx >= 1:
                # 2-layer Sequential
                model.fc = nn.Sequential(
                    nn.Linear(in_features, 512),    # Index 0
                    nn.Linear(512, num_classes)     # Index 1
                )
                logger.info(f"[ML] Detected Sequential fc (2 layers) with {num_classes} classes")
            else:
                # Single Linear
                model.fc = nn.Linear(in_features, num_classes)
                logger.info(f"[ML] Detected Linear fc with {num_classes} classes")
        else:
            # Fallback to Linear
            model.fc = nn.Linear(in_features, num_classes)
            logger.info(f"[ML] Fallback to Linear fc with {num_classes} classes")

    # 7. Load state_dict
    try:
        incompatible = model.load_state_dict(state_dict, strict=False)
        if incompatible.missing_keys:
            logger.warning(f"[ML] Missing keys ({len(incompatible.missing_keys)}): {incompatible.missing_keys[:5]}")
        if incompatible.unexpected_keys:
            logger.warning(f"[ML] Unexpected keys ({len(incompatible.unexpected_keys)}): {incompatible.unexpected_keys[:5]}")
    except RuntimeError as e:
        logger.error(f"[ML] FAILED to load state_dict: {str(e)}")
        raise RuntimeError(f"Model loading failed for {key}: {str(e)}")
    
    # 8. Convert to float32 and eval
    model = model.float()
    model.eval()
    logger.info(f"[ML] ✅ {key} loaded successfully (num_classes={num_classes})")
    return model



def get_cached_model(key: str) -> nn.Module:
    """Global singleton pattern for models."""
    global _model_cache
    if key not in _model_cache:
        with _cache_lock:
            if key not in _model_cache:
                _model_cache[key] = load_model_from_checkpoint(key)
    return _model_cache[key]

# --- Preprocessing ---

def preprocess_image(image_bytes: bytes) -> torch.Tensor:
    """ImageNet-norm preprocessing (NCHW)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224), Image.BILINEAR)
    
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    
    arr = arr.transpose(2, 0, 1) # NCHW
    tensor = torch.from_numpy(arr).unsqueeze(0)
    return tensor.float()

def get_label_data(logits: torch.Tensor, labels: list) -> Tuple[str, float, Dict[str, float]]:
    probs = torch.softmax(logits, dim=1).squeeze().tolist()
    if not isinstance(probs, list): probs = [probs]
    
    idx = int(torch.argmax(logits, dim=1).item())
    label = labels[idx]
    confidence = float(probs[idx] * 100.0)
    
    prob_dict = {name: round(p * 100, 2) for name, p in zip(labels, probs)}
    return label, confidence, prob_dict

# --- Pipelines ---

def predict_lung_cancer(image_bytes: bytes) -> dict:
    """Lung cancer prediction with error handling."""
    try:
        tensor = preprocess_image(image_bytes)
        model = get_cached_model("lung")
        with torch.no_grad():
            logits = model(tensor)
        
        label, conf, probs = get_label_data(logits, LUNG_LABELS)
        return {
            "disease": "lung",
            "prediction": label,
            "confidence": round(conf, 2),
            "class_probabilities": probs
        }
    except Exception as e:
        logger.error(f"[ML] Lung cancer prediction failed: {str(e)}", exc_info=True)
        raise

def predict_diabetic_retinopathy(image_bytes: bytes) -> dict:
    """Diabetic retinopathy prediction with error handling."""
    try:
        tensor = preprocess_image(image_bytes)
        
        # Stage 1: Assessment
        m1 = get_cached_model("dr_stage1")
        with torch.no_grad():
            l1 = m1(tensor)
        label1, conf1, probs1 = get_label_data(l1, DR_STAGE1_LABELS)
        
        if label1 == "No DR":
            return {
                "disease": "diabetic_retinopathy",
                "prediction": label1,
                "confidence": round(conf1, 2),
                "class_probabilities": probs1,
                "stage1_result": label1,
                "stage2_result": None
            }
        
        # Stage 2: Severity check
        m2 = get_cached_model("dr_stage2")
        with torch.no_grad():
            l2 = m2(tensor)
        label2, conf2, probs2 = get_label_data(l2, DR_STAGE2_LABELS)
        
        return {
            "disease": "diabetic_retinopathy",
            "prediction": label2,
            "confidence": round(conf2, 2),
            "class_probabilities": probs2,
            "stage1_result": label1,
            "stage2_result": label2
        }
    except Exception as e:
        logger.error(f"[ML] DR prediction failed: {str(e)}", exc_info=True)
        raise

def predict_skin_disease(image_bytes: bytes) -> dict:
    """Skin disease prediction with error handling."""
    try:
        tensor = preprocess_image(image_bytes)
        
        # Stage 1: Broad Category
        m1 = get_cached_model("skin_stage1")
        with torch.no_grad():
            l1 = m1(tensor)
        label1, conf1, probs1 = get_label_data(l1, SKIN_STAGE1_LABELS)
        
        # Stage 2: Subtype
        if label1 == "Benign":
            m2 = get_cached_model("skin_benign")
            labs2 = SKIN_BENIGN_LABELS
        else:
            m2 = get_cached_model("skin_malignant")
            labs2 = SKIN_MALIGNANT_LABELS
        
        with torch.no_grad():
            l2 = m2(tensor)
        label2, conf2, probs2 = get_label_data(l2, labs2)
    
        prediction = f"{label1} ({label2})"
        
        return {
            "disease": "skin",
            "prediction": prediction,
            "confidence": round(conf2, 2),
            "class_probabilities": probs2,
            "stage1_result": label1,
            "stage2_result": label2
        }
    except Exception as e:
        logger.error(f"[ML] Skin disease prediction failed: {str(e)}", exc_info=True)
        raise

# --- Utilities ---

def get_model_status() -> Dict[str, Dict[str, Any]]:
    return {k: {"path": str(v), "exists": v.exists(), "loaded": k in _model_cache} 
            for k, v in MODEL_PATHS.items()}

def get_loaded_model_for_disease(disease: str) -> Tuple[Optional[nn.Module], Optional[str]]:
    mapping = {
        "lung-cancer": "lung",
        "skin-disease": "skin_stage1",
        "diabetic-retinopathy": "dr_stage1"
    }
    key = mapping.get(disease, disease.replace("-", "_"))
    try:
        return get_cached_model(key), "torch"
    except Exception:
        return None, None
