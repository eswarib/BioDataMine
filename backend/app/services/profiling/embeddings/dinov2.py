# =========================
# profiling/embeddings/dinov2_embedder.py
# =========================

import torch
from torchvision import transforms
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Any
from .BaseEmbedder import BaseEmbedder


class DinoV2Embedder(BaseEmbedder):
    MEAN = [0.485, 0.456, 0.406]
    STD = [0.229, 0.224, 0.225]

    def __init__(self, model_name: str = "dinov2_vitb14", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = self.load_model()
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.MEAN,
                std=self.STD,
            ),
        ])

    def load_model(self):
        # Load model from torch hub
        model = torch.hub.load("facebookresearch/dinov2", self.model_name)
        model.eval()
        model.to(self.device)
        return model

    def preprocess(self, image: Image.Image):
        if image.mode != "RGB":
            image = image.convert("RGB")
        return self.transform(image).unsqueeze(0).to(self.device)

    @torch.no_grad()
    def embed(self, image: Image.Image) -> np.ndarray:
        x = self.preprocess(image)
        embedding = self.model(x)
        return embedding.squeeze(0).cpu().numpy()


def extract_embeddings(image: np.ndarray, filename: str) -> dict[str, Any]:
    """
    Stand-alone helper to extract DINOv2 embeddings for a single image.
    Returns the requested JSON format.
    """
    # Lazy initialization of embedder to avoid loading model on import
    # In a production environment, we'd use a singleton or global instance
    global _dino_embedder
    if "_dino_embedder" not in globals():
        # Default to CPU for safety in various environments, can be changed to 'cuda' if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _dino_embedder = DinoV2Embedder(device=device)

    # Convert numpy array (H, W, C) to PIL Image
    pil_img = Image.fromarray(image)
    
    # Extract embedding
    emb = _dino_embedder.embed(pil_img)
    
    return {
        "image_id": Path(filename).name,
        "embedding": emb.tolist(),
        "model": _dino_embedder.model_name,
    }
