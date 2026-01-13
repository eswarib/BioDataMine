import numpy as np
import re
import logging
from pathlib import Path

try:
    import cv2
except ImportError:  # allow running without OpenCV; edge density will be skipped
    cv2 = None

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import timm
    from torchvision import transforms
    from PIL import Image
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)

# Modality classes in fixed order for consistent indexing
MODALITY_CLASSES = ["CT", "MR", "XRAY", "US", "OPTICAL"]


class ModalityCNN:
    """
    CNN-based modality classifier using a pretrained backbone.
    
    Uses EfficientNet-B0 by default with a custom classification head.
    Supports loading fine-tuned weights if available.
    """
    
    MEAN = [0.485, 0.456, 0.406]
    STD = [0.229, 0.224, 0.225]
    
    def __init__(
        self,
        backbone: str = "efficientnet_b0",
        weights_path: str | None = None,
        device: str | None = None,
    ):
        self.backbone_name = backbone
        self.weights_path = weights_path
        self.num_classes = len(MODALITY_CLASSES)
        
        # Auto-select device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.model = self._load_model()
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.MEAN, std=self.STD),
        ])
        
    def _load_model(self) -> nn.Module:
        """Load the backbone and classification head."""
        # Create model with custom number of classes
        model = timm.create_model(
            self.backbone_name,
            pretrained=True,
            num_classes=self.num_classes,
        )
        
        # Load fine-tuned weights if provided
        if self.weights_path and Path(self.weights_path).exists():
            logger.info("Loading fine-tuned weights from %s", self.weights_path)
            state_dict = torch.load(self.weights_path, map_location=self.device)
            model.load_state_dict(state_dict)
        else:
            logger.info(
                "No fine-tuned weights found, using pretrained %s backbone. "
                "Predictions will be based on transfer learning features.",
                self.backbone_name
            )
            
        model.eval()
        model.to(self.device)
        return model
    
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess a numpy image for inference.
        
        Args:
            image: numpy array of shape (H, W) or (H, W, C)
            
        Returns:
            Preprocessed tensor of shape (1, 3, 224, 224)
        """
        # Convert grayscale to RGB
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[2] == 1:
            image = np.concatenate([image] * 3, axis=-1)
        elif image.shape[2] == 4:  # RGBA
            image = image[..., :3]
            
        # Ensure uint8
        if image.dtype != np.uint8:
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = image.astype(np.uint8)
                
        pil_img = Image.fromarray(image)
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
            
        return self.transform(pil_img).unsqueeze(0).to(self.device)
    
    @torch.inference_mode()
    def predict(self, image: np.ndarray, return_embedding: bool = False) -> dict[str, float] | tuple[dict[str, float], np.ndarray]:
        """
        Run inference on a single image.
        
        Args:
            image: numpy array of shape (H, W) or (H, W, C)
            return_embedding: If True, also return the feature embedding
            
        Returns:
            Dictionary mapping modality names to probabilities.
            If return_embedding=True, returns (probs_dict, embedding_array)
        """
        x = self.preprocess(image)
        
        if return_embedding:
            # Extract features before classification head
            features = self.model.forward_features(x)
            # Global average pooling if needed (for CNN backbones)
            if len(features.shape) == 4:  # (B, C, H, W)
                features = features.mean(dim=[2, 3])  # -> (B, C)
            elif len(features.shape) == 3:  # (B, N, C) for ViT
                features = features[:, 0]  # CLS token or mean
            
            # Get classification logits
            logits = self.model.forward_head(features)
            probs = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
            embedding = features.squeeze(0).cpu().numpy()
            
            probs_dict = {cls: float(prob) for cls, prob in zip(MODALITY_CLASSES, probs)}
            return probs_dict, embedding
        else:
            logits = self.model(x)
            probs = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
            return {cls: float(prob) for cls, prob in zip(MODALITY_CLASSES, probs)}
    
    @torch.inference_mode()
    def extract_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Extract only the feature embedding (no classification).
        
        Args:
            image: numpy array of shape (H, W) or (H, W, C)
            
        Returns:
            Feature embedding as numpy array
        """
        x = self.preprocess(image)
        features = self.model.forward_features(x)
        
        # Global average pooling if needed
        if len(features.shape) == 4:  # (B, C, H, W)
            features = features.mean(dim=[2, 3])
        elif len(features.shape) == 3:  # (B, N, C) for ViT
            features = features[:, 0]
            
        return features.squeeze(0).cpu().numpy()
    
    @torch.inference_mode()
    def predict_batch(self, images: list[np.ndarray]) -> list[dict[str, float]]:
        """Run inference on a batch of images."""
        tensors = [self.preprocess(img) for img in images]
        batch = torch.cat(tensors, dim=0)
        logits = self.model(batch)
        probs = F.softmax(logits, dim=-1).cpu().numpy()
        
        return [
            {cls: float(p) for cls, p in zip(MODALITY_CLASSES, row)}
            for row in probs
        ]


# Global singleton for lazy initialization
_modality_cnn: ModalityCNN | None = None


def _get_modality_cnn() -> ModalityCNN | None:
    """Get or initialize the modality CNN classifier."""
    global _modality_cnn
    
    if not _TORCH_AVAILABLE:
        logger.warning("PyTorch not available, CNN predictions disabled")
        return None
        
    if _modality_cnn is None:
        from app.core.config import settings
        
        logger.info(
            "Initializing modality CNN classifier (backbone=%s, device=%s)",
            settings.modality_cnn_backbone,
            settings.modality_cnn_device or "auto",
        )
        _modality_cnn = ModalityCNN(
            backbone=settings.modality_cnn_backbone,
            weights_path=settings.modality_cnn_weights_path,
            device=settings.modality_cnn_device,
        )
        
    return _modality_cnn


def _cnn_predict(
    image: np.ndarray,
    return_embedding: bool = False,
) -> dict[str, float] | tuple[dict[str, float], np.ndarray | None]:
    """
    Run CNN-based modality prediction on an image.
    
    Args:
        image: numpy array of shape (H, W) or (H, W, C)
        return_embedding: If True, also return the feature embedding
        
    Returns:
        Dictionary mapping modality names to probabilities.
        If return_embedding=True, returns (probs_dict, embedding_array or None).
        Returns uniform distribution if model unavailable.
    """
    cnn = _get_modality_cnn()
    uniform = {cls: 1.0 / len(MODALITY_CLASSES) for cls in MODALITY_CLASSES}
    
    if cnn is None:
        return (uniform, None) if return_embedding else uniform
    
    try:
        if return_embedding:
            probs, embedding = cnn.predict(image, return_embedding=True)
            return probs, embedding
        return cnn.predict(image)
    except Exception as e:
        logger.warning("CNN prediction failed: %s, using uniform fallback", e)
        return (uniform, None) if return_embedding else uniform


def infer_modality(
    image: np.ndarray,
    filename: str,
    foldernames: list[str],
    ocr_text: str = "",
    image_path: str | None = None,
    dataset_id: str | None = None,
) -> dict:
    """
    Infer the imaging modality of a medical image.
    
    Args:
        image: numpy array of shape (H, W) or (H, W, C)
        filename: Name of the image file
        foldernames: Parent folder names for heuristics
        ocr_text: Optional OCR text extracted from image
        image_path: Full path to image (for logging)
        dataset_id: Dataset identifier (for logging)
        
    Returns:
        Dictionary with prediction, confidence, and details
    """
    from app.core.config import settings
    
    votes = {k: 0.0 for k in ["CT", "MR", "XRAY", "US", "OPTICAL", "OTHER"]}
    details = {}

    # Check if we need embeddings for logging
    need_embedding = (
        settings.prediction_log_enabled 
        and settings.prediction_log_include_embeddings
    )
    
    # CNN output (with optional embedding extraction)
    embedding = None
    if need_embedding:
        cnn_probs, embedding = _cnn_predict(image, return_embedding=True)
    else:
        cnn_probs = _cnn_predict(image)
    details["cnn_probs"] = cnn_probs

    # Aspect ratio
    h, w = image.shape[:2]
    aspect = w / h
    details["aspect_ratio"] = aspect
    if 0.7 < aspect < 1.5:
        votes["US"] += 0.2
        votes["MR"] += 0.2

    # Grayscale vs color
    if len(image.shape) == 2 or (image.shape[2] == 1 or (np.allclose(image[...,0], image[...,1]) and np.allclose(image[...,1], image[...,2]))):
        votes["CT"] += 0.2
        votes["MR"] += 0.2
        votes["XRAY"] += 0.2
    else:
        votes["OPTICAL"] += 0.3

    # Intensity histogram
    hist = np.histogram(image, bins=32)[0]
    details["intensity_hist"] = hist[:5].tolist()

    # Edge density
    edge_density = 0.0
    if cv2 is not None:
        try:
            edges = cv2.Canny(image, 100, 200)
            edge_density = float(np.mean(edges > 0))
            details["edge_density"] = edge_density
            if edge_density > 0.2:
                votes["XRAY"] += 0.15
        except Exception:
            edge_density = 0.0

    # Filename/folder heuristics
    namejoined = f"{filename} {' '.join(foldernames)}".lower()
    if re.search(r"\bus\b|us_|ultrasound", namejoined):
        votes["US"] += 1
    if re.search(r"\bct\b|ctscan", namejoined):
        votes["CT"] += 1
    if re.search(r"\bmr\b|mri", namejoined):
        votes["MR"] += 1
    if "xray" in namejoined or "cr" in namejoined or "dx" in namejoined:
        votes["XRAY"] += 1

    # OCR heuristic
    ocr = ocr_text.lower() if ocr_text else ""
    if "mhz" in ocr or "depth" in ocr or "gain" in ocr:
        votes["US"] += 0.8
    if "kvp" in ocr or "mas" in ocr:
        votes["XRAY"] += 0.8
    if "te" in ocr or "tr" in ocr:
        votes["MR"] += 0.8

    # Add CNN probabilities
    for k, p in cnn_probs.items():
        votes[k] += p

    # Final decision
    pred = max(votes, key=votes.get)
    winner_score = votes[pred]
    sum_votes = sum(max(v, 0) for v in votes.values())
    confidence = winner_score / sum_votes if sum_votes else 0.0

    result = {
        "pred": pred,
        "confidence": float(confidence),
        "version": "v1.0.0",
        "method": "cnn+heuristics",
        "probs": cnn_probs,
        "heuristic_votes": votes,
        "sources": ["cnn", "heuristics"],
        "details": details,
    }
    
    # Log prediction for future retraining
    _log_prediction(
        image_path=image_path or filename,
        prediction=pred,
        confidence=confidence,
        probabilities=cnn_probs,
        dataset_id=dataset_id,
        heuristic_votes=votes,
        embedding=embedding,
    )
    
    return result


def _log_prediction(
    image_path: str,
    prediction: str,
    confidence: float,
    probabilities: dict[str, float],
    dataset_id: str | None = None,
    heuristic_votes: dict[str, float] | None = None,
    embedding: np.ndarray | None = None,
) -> None:
    """Log a prediction for future retraining (async-safe, non-blocking)."""
    try:
        from .prediction_logger import get_prediction_logger
        
        pred_logger = get_prediction_logger()
        if pred_logger is None:
            return
        
        # Get model info from the CNN singleton
        cnn = _get_modality_cnn()
        model_info = {
            "backbone": cnn.backbone_name if cnn else "unknown",
            "weights_path": cnn.weights_path if cnn else None,
            "version": "v1.0.0",
        }
        
        # Convert embedding to list for JSON serialization
        embedding_list = embedding.tolist() if embedding is not None else None
        
        pred_logger.log_prediction(
            image_path=image_path,
            prediction=prediction,
            confidence=confidence,
            probabilities=probabilities,
            model_info=model_info,
            dataset_id=dataset_id,
            embedding=embedding_list,
            extra_metadata={"heuristic_votes": heuristic_votes} if heuristic_votes else None,
        )
    except Exception as e:
        # Never let logging failures break inference
        logger.debug("Prediction logging failed (non-critical): %s", e)

