# =========================
# profiling/pipeline.py
# =========================

"""
High-level orchestration script.
"""

from pathlib import Path


def run_profiling(image_dir: str, output_dir: str):
    image_dir = Path(image_dir)
    output_dir = Path(output_dir)

    # 1. DINOv2 embeddings
    dino = DinoV2Embedder()
    run_embedding(image_dir, dino, output_dir / "dinov2")

    # 2. EfficientNet embeddings
    eff = EfficientNetRadImageNetEmbedder()
    run_embedding(image_dir, eff, output_dir / "efficientnet")

    # 3. Clustering (example using DINOv2)
    embeddings = np.load(output_dir / "dinov2" / "embeddings.npy")
    cluster_info = cluster_embeddings(embeddings)

    # 4. Summary
    summary = summarize_clusters(cluster_info["labels"])

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary

