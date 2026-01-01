"""Dataset-level modality summary helpers."""

from __future__ import annotations
from collections import Counter
from typing import List, Dict, Any


def summarize_dataset_profiling(
    modality_preds: List[str], 
    modality_confidences: List[float | None],
    cluster_labels: List[int],
    outliers_count: int
) -> dict[str, Any]:
    """
    Creates a detailed modality summary including mixed-modality flags and outliers.
    """
    cnt = Counter(modality_preds)
    total = sum(cnt.values()) or 1
    
    # Calculate average confidence per modality
    mod_conf: Dict[str, List[float]] = {}
    for mod, conf in zip(modality_preds, modality_confidences):
        if conf is not None:
            if mod not in mod_conf:
                mod_conf[mod] = []
            mod_conf[mod].append(conf)
            
    modalities_summary = {}
    for mod, count in cnt.items():
        summary = {"percent": round((count / total) * 100, 2)}
        if mod in mod_conf and mod_conf[mod]:
            summary["confidence"] = round(sum(mod_conf[mod]) / len(mod_conf[mod]), 4)
        modalities_summary[mod] = summary

    # Heuristic for mixed modality: if second most common modality is > 15%
    sorted_counts = cnt.most_common()
    mixed_modality = False
    if len(sorted_counts) > 1:
        second_mod_percent = (sorted_counts[1][1] / total) * 100
        if second_mod_percent > 15:
            mixed_modality = True

    return {
        "modalities": modalities_summary,
        "mixed_modality": mixed_modality,
        "outliers": outliers_count
    }




