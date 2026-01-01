"""
BioDataMine – Inference Module Skeletons
======================================

This file sketches the *exact Python module structure* for using
inference models for modality detection.

Philosophy:
- takes in embeddings and returns modality predictions
- does not require raw images
- Everything reproducible and inspectable
"""

# =========================
# inference/modality/base.py
# =========================

from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np


class BaseModalityInference(ABC):
    """Abstract base class for all modality inference models."""

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    def preprocess(self, image):
        pass

    @abstractmethod
    def infer(self, image) -> np.ndarray:
        pass

    def infer_batch(self, images: List) -> np.ndarray:
        return np.stack([self.embed(img) for img in images])





# =========================
# profiling/embeddings/runner.py
# =========================

import json
from pathlib import Path
from PIL import Image


def run_modality_inference(
    image_dir: Path,
    modality_inference: BaseModalityInference,
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    modality_predictions = []
    
        


