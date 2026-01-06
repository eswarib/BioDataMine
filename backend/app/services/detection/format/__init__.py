"""File format detection (DICOM/NIfTI/images/etc)."""

from app.services.detection.format.sniff import sniff_file

__all__ = ["sniff_file"]







