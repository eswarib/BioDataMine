"""HDBSCAN clustering for image embeddings."""

from __future__ import annotations
import hdbscan
import numpy as np
from sklearn.preprocessing import normalize


def cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int = 10, use_cosine: bool = True) -> dict:
    """
    Clusters embeddings using HDBSCAN.
    If use_cosine is True, normalizes embeddings to unit length and uses euclidean distance.
    """
    if use_cosine:
        embeddings = normalize(embeddings, axis=1)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean"
    )
    labels = clusterer.fit_predict(embeddings)

    return {
        "labels": labels.tolist(),
        "n_clusters": len(set(labels)) - (1 if -1 in labels else 0),
        "outliers": int((labels == -1).sum())
    }




