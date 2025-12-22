from __future__ import annotations

from pathlib import Path


def sniff_file(path: Path) -> dict:
    """
    Return a best-effort classification for the file.
    Output shape:
      {
        kind: "dicom|nifti|image|unknown",
        modality: "CT|MR|DX|US|...|unknown",
        ndim: int|None,
        dims: [..]|None,
        size_bytes: int,
        meta: {...}
      }
    """
    size_bytes = _safe_stat_size(path)
    suffix = "".join(path.suffixes).lower()

    # NIfTI
    if suffix.endswith(".nii") or suffix.endswith(".nii.gz"):
        return _sniff_nifti(path, size_bytes)

    # DICOM: try magic then pydicom
    if _looks_like_dicom(path) or suffix.endswith(".dcm"):
        d = _sniff_dicom(path, size_bytes)
        if d:
            return d

    # 2D images
    if suffix.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")):
        return _sniff_image(path, size_bytes)

    return {"kind": "unknown", "modality": "unknown", "ndim": None, "dims": None, "size_bytes": size_bytes, "meta": {}}


def _sniff_dicom(path: Path, size_bytes: int) -> dict | None:
    try:
        import pydicom

        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        modality = getattr(ds, "Modality", None) or "unknown"
        body_part = getattr(ds, "BodyPartExamined", None)
        rows = getattr(ds, "Rows", None)
        cols = getattr(ds, "Columns", None)
        dims = None
        if isinstance(rows, int) and isinstance(cols, int):
            dims = [cols, rows]
        return {
            "kind": "dicom",
            "modality": str(modality),
            "ndim": 2,  # single DICOM instance is 2D; 3D detected at series-level later
            "dims": dims,
            "size_bytes": size_bytes,
            "meta": {
                "SOPClassUID": getattr(ds, "SOPClassUID", None),
                "SeriesInstanceUID": getattr(ds, "SeriesInstanceUID", None),
                "StudyInstanceUID": getattr(ds, "StudyInstanceUID", None),
                "BodyPartExamined": body_part,
            },
        }
    except Exception:
        return None


def _sniff_nifti(path: Path, size_bytes: int) -> dict:
    try:
        import nibabel as nib

        img = nib.load(str(path))
        shape = tuple(int(x) for x in img.shape)
        ndim = len(shape)
        dims = list(shape)
        return {"kind": "nifti", "modality": "unknown", "ndim": ndim, "dims": dims, "size_bytes": size_bytes, "meta": {}}
    except Exception:
        return {"kind": "nifti", "modality": "unknown", "ndim": None, "dims": None, "size_bytes": size_bytes, "meta": {}}


def _sniff_image(path: Path, size_bytes: int) -> dict:
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
        return {"kind": "image", "modality": "unknown", "ndim": 2, "dims": [w, h], "size_bytes": size_bytes, "meta": {}}
    except Exception:
        return {"kind": "image", "modality": "unknown", "ndim": 2, "dims": None, "size_bytes": size_bytes, "meta": {}}


def _looks_like_dicom(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            preamble = f.read(132)
        return len(preamble) >= 132 and preamble[128:132] == b"DICM"
    except Exception:
        return False


def _safe_stat_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return 0


