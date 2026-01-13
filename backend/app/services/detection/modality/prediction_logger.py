"""
Prediction Logger for Modality CNN

Logs predictions to JSONL files for later retraining and analysis.
Each prediction is stored with metadata to enable:
- Periodic fine-tuning on new data
- Active learning (human review of low-confidence predictions)
- Model performance monitoring over time
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class PredictionLogger:
    """
    Thread-safe logger for CNN predictions.
    
    Writes predictions to daily JSONL files for easy processing.
    Automatically creates directories and rotates files by date.
    """
    
    def __init__(
        self,
        log_dir: str | Path,
        low_confidence_threshold: float = 0.6,
        include_embeddings: bool = False,
    ):
        self.log_dir = Path(log_dir)
        self.low_confidence_threshold = low_confidence_threshold
        self.include_embeddings = include_embeddings
        self._lock = Lock()
        self._current_date: str | None = None
        self._current_file: Path | None = None
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.log_dir / "needs_review").mkdir(exist_ok=True)
        
        logger.info(
            "PredictionLogger initialized: dir=%s, low_conf_threshold=%.2f",
            self.log_dir, self.low_confidence_threshold
        )
    
    def _get_log_file(self, needs_review: bool = False) -> Path:
        """Get the current log file path, rotating daily."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if needs_review:
            return self.log_dir / "needs_review" / f"predictions_{today}.jsonl"
        return self.log_dir / f"predictions_{today}.jsonl"
    
    def log_prediction(
        self,
        image_path: str,
        prediction: str,
        confidence: float,
        probabilities: dict[str, float],
        model_info: dict[str, Any],
        dataset_id: str | None = None,
        embedding: list[float] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Log a single prediction.
        
        Args:
            image_path: Path to the image file
            prediction: Predicted modality class
            confidence: Confidence score (0-1)
            probabilities: Dict of class -> probability
            model_info: Model metadata (backbone, version, etc.)
            dataset_id: Optional dataset identifier
            embedding: Optional embedding vector (if include_embeddings=True)
            extra_metadata: Any additional metadata to store
            
        Returns:
            The logged record (for inspection/testing)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        needs_review = confidence < self.low_confidence_threshold
        
        record = {
            "timestamp": timestamp,
            "image_path": str(image_path),
            "dataset_id": dataset_id,
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "needs_review": needs_review,
            "human_label": None,  # To be filled during review
            "reviewed_at": None,
            "model": model_info,
        }
        
        if extra_metadata:
            record["metadata"] = extra_metadata
            
        if self.include_embeddings and embedding is not None:
            record["embedding"] = embedding
        
        # Write to appropriate file
        log_file = self._get_log_file(needs_review=needs_review)
        
        with self._lock:
            with open(log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        
        if needs_review:
            logger.debug(
                "Low confidence prediction logged for review: %s -> %s (%.2f)",
                image_path, prediction, confidence
            )
        
        return record
    
    def get_review_queue(self, limit: int = 100) -> list[dict]:
        """
        Get predictions that need human review.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of prediction records needing review
        """
        review_dir = self.log_dir / "needs_review"
        records = []
        
        for jsonl_file in sorted(review_dir.glob("*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("human_label") is None:
                        records.append(record)
                        if len(records) >= limit:
                            return records
        
        return records
    
    def submit_review(
        self,
        image_path: str,
        human_label: str,
        reviewer_id: str | None = None,
    ) -> bool:
        """
        Submit a human review/correction for a prediction.
        
        This creates a separate reviewed file that can be used for retraining.
        
        Args:
            image_path: Path to the image
            human_label: The correct label from human review
            reviewer_id: Optional identifier for the reviewer
            
        Returns:
            True if review was recorded successfully
        """
        reviewed_file = self.log_dir / "reviewed_labels.jsonl"
        
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image_path": str(image_path),
            "human_label": human_label,
            "reviewer_id": reviewer_id,
        }
        
        with self._lock:
            with open(reviewed_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        
        logger.info("Review submitted: %s -> %s", image_path, human_label)
        return True
    
    def export_training_data(self, output_path: str | Path) -> dict[str, int]:
        """
        Export reviewed predictions as training data.
        
        Creates a JSONL file with image_path and label columns,
        ready for fine-tuning.
        
        Args:
            output_path: Path for the output file
            
        Returns:
            Statistics about exported data
        """
        reviewed_file = self.log_dir / "reviewed_labels.jsonl"
        output_path = Path(output_path)
        
        if not reviewed_file.exists():
            logger.warning("No reviewed labels found")
            return {"total": 0, "exported": 0}
        
        stats = {"total": 0, "exported": 0, "by_class": {}}
        
        with open(reviewed_file) as f_in, open(output_path, "w") as f_out:
            for line in f_in:
                stats["total"] += 1
                record = json.loads(line)
                
                export_record = {
                    "image_path": record["image_path"],
                    "label": record["human_label"],
                }
                f_out.write(json.dumps(export_record) + "\n")
                
                stats["exported"] += 1
                label = record["human_label"]
                stats["by_class"][label] = stats["by_class"].get(label, 0) + 1
        
        logger.info(
            "Exported %d training samples to %s",
            stats["exported"], output_path
        )
        return stats


# Global singleton
_prediction_logger: PredictionLogger | None = None


def get_prediction_logger() -> PredictionLogger | None:
    """Get or initialize the prediction logger."""
    global _prediction_logger
    
    from app.core.config import settings
    
    if not settings.prediction_log_enabled:
        return None
    
    if _prediction_logger is None:
        _prediction_logger = PredictionLogger(
            log_dir=settings.prediction_log_path,
            low_confidence_threshold=settings.prediction_log_low_confidence_threshold,
            include_embeddings=settings.prediction_log_include_embeddings,
        )
    
    return _prediction_logger


