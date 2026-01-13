"""
Pipeline helper functions.

Shared utility functions used by the dataset pipeline and other modules.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path


class PipelineHelpers:
    """
    Static utility functions for the dataset pipeline.
    
    These functions are stateless and can be used by any module.
    """

    @staticmethod
    def iter_files(root: Path, limit: int):
        """
        Yield file paths under root directory, up to limit.
        
        Args:
            root: Root directory to scan
            limit: Maximum number of files to yield
            
        Yields:
            Path objects for each file found
        """
        n = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                yield Path(dirpath) / fn
                n += 1
                if n >= limit:
                    return

    @staticmethod
    def file_ext(path: Path) -> str:
        """
        Extract file extension, handling compound extensions like .nii.gz.
        
        Args:
            path: File path
            
        Returns:
            Lowercase extension string (e.g., ".png", ".nii.gz", "none")
        """
        sfx = [s.lower() for s in path.suffixes]
        if not sfx:
            return "none"
        if len(sfx) >= 2 and sfx[-2:] == [".nii", ".gz"]:
            return ".nii.gz"
        return sfx[-1]

    @staticmethod
    def object_id(s: str):
        """
        Convert string to MongoDB ObjectId.
        
        Args:
            s: String representation of ObjectId
            
        Returns:
            bson.ObjectId instance
        """
        from bson import ObjectId
        return ObjectId(s)

    @staticmethod
    def accumulate_counts(
        doc: dict,
        fp: Path,
        modality_counts: Counter[str],
        kind_counts: Counter[str],
        ext_counts: Counter[str],
        dicom_series_counts: Counter[str],
    ) -> None:
        """
        Update counters based on analyzed file document.
        
        Args:
            doc: File document with 'modality', 'kind', 'meta' fields
            fp: File path
            modality_counts: Counter for modalities
            kind_counts: Counter for file kinds
            ext_counts: Counter for file extensions
            dicom_series_counts: Counter for DICOM series UIDs
        """
        modality = doc.get("modality") or "unknown"
        modality_counts[modality] += 1

        kind = doc.get("kind") or "unknown"
        kind_counts[str(kind)] += 1

        ext_counts[PipelineHelpers.file_ext(fp)] += 1

        if kind == "dicom":
            series_uid = (doc.get("meta") or {}).get("SeriesInstanceUID")
            if series_uid:
                dicom_series_counts[str(series_uid)] += 1

    @staticmethod
    def build_modalities_profile(modality_counts: Counter[str], total_files: int) -> dict:
        """
        Build modality profile structure for dataset summary.
        
        Args:
            modality_counts: Counter of modality occurrences
            total_files: Total number of files in dataset
            
        Returns:
            Dict like:
            {
              "Ultrasound": {"percent": 63.0, "confidence": None},
              "X-ray": {"percent": 22.0, "confidence": None},
              "Unknown": {"percent": 15.0, "confidence": None}
            }
        """
        res: dict[str, dict] = {}
        denom = total_files or 1
        for modality, count in modality_counts.items():
            pct = (count / denom) * 100.0
            entry = {"percent": pct, "confidence": None}
            res[str(modality)] = entry
        return res

    @staticmethod
    def is_mixed_modality(modality_counts: Counter[str]) -> bool:
        """
        Check if dataset contains multiple modalities.
        
        Args:
            modality_counts: Counter of modality occurrences
            
        Returns:
            True if more than one non-zero modality (excluding 'unknown')
        """
        non_zero = [m for m, c in modality_counts.items() if c > 0 and m != "unknown"]
        return len(non_zero) > 1
