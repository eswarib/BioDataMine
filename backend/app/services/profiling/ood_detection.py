"""Out-of-distribution detection stubs."""

from __future__ import annotations

import numpy as np


def score_ood(embeddings: np.ndarray) -> np.ndarray:
    """
    Stub OOD scorer: returns zero scores for all samples.
    Replace with a distance-to-centroid or density estimator.
    """
    return np.zeros(embeddings.shape[0], dtype=np.float32)




