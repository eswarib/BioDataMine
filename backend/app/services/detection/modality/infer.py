import numpy as np
import re

try:
    import cv2
except ImportError:  # allow running without OpenCV; edge density will be skipped
    cv2 = None

# Placeholder for CNN model call
def _cnn_predict(image: np.ndarray) -> dict:
    # In reality, this would call your model and return class: probability
    # EXAMPLE: return {"CT": 0.7, "US": 0.2, "MR": 0.05, "XRAY": 0.05, "OPTICAL": 0.0}
    return {"CT": 0.2, "US": 0.2, "MR": 0.2, "XRAY": 0.2, "OPTICAL": 0.2}


def infer_modality(image: np.ndarray, filename: str, foldernames: list[str], ocr_text: str = "") -> dict:
    votes = {k: 0.0 for k in ["CT", "MR", "XRAY", "US", "OPTICAL", "OTHER"]}
    details = {}

    # CNN output
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

    return {
        "pred": pred,
        "confidence": float(confidence),
        "version": "v1.0.0",
        "method": "cnn+heuristics",
        "probs": cnn_probs,
        "heuristic_votes": votes,
        "sources": ["cnn", "heuristics"],
        "details": details,
    }

