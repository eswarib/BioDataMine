"""
BioDataMine – Profiling Module Skeletons
======================================

This file sketches the *exact Python module structure* for using
DINOv2 and EfficientNet-B3 (RadImageNet) for dataset profiling.

Philosophy:
- No hard labels by default
- Embeddings first, inference later
- Everything reproducible and inspectable
"""

# =========================
# profiling/embeddings/base.py
# =========================

from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np


class BaseEmbedder(ABC):
    """Abstract base class for all embedding models."""

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    def preprocess(self, image):
        pass

    @abstractmethod
    def embed(self, image) -> np.ndarray:
        pass

    def embed_batch(self, images: List) -> np.ndarray:
        return np.stack([self.embed(img) for img in images])






# =========================
# profiling/clustering/hdbscan_cluster.py
# =========================

import hdbscan


def cluster_embeddings(embeddings: np.ndarray):
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=50,
        metric="euclidean"
    )
    labels = clusterer.fit_predict(embeddings)

    return {
        "labels": labels.tolist(),
        "n_clusters": len(set(labels)) - (1 if -1 in labels else 0),
        "outliers": int((labels == -1).sum())
    }


# =========================
# profiling/summaries/modality_summary.py
# =========================

from collections import Counter


def summarize_clusters(cluster_labels):
    counts = Counter(cluster_labels)
    total = sum(counts.values())

    summary = {}
    for label, count in counts.items():
        key = "outlier" if label == -1 else f"cluster_{label}"
        summary[key] = {
            "count": count,
            "percent": round(100 * count / total, 2)
        }

    return summary


