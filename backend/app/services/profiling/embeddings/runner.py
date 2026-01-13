# =========================
# profiling/embeddings/runner.py
# =========================

import json
from pathlib import Path
from PIL import Image


def run_embedding(
    image_dir: Path,
    embedder: BaseEmbedder,
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    embeddings = []
    index = []

    for img_path in image_dir.glob("**/*"):
        if img_path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
            continue

        image = Image.open(img_path)
        emb = embedder.embed(image)

        embeddings.append(emb)
        index.append({
            "image_path": str(img_path),
            "embedding_dim": emb.shape[0]
        })

    np.save(output_dir / "embeddings.npy", np.stack(embeddings))
    with open(output_dir / "index.json", "w") as f:
        json.dump(index, f, indent=2)
