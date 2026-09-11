"""
Data Models for Strategy Scoring and Performance Evaluation.
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class StrategyScore:
    """
    Performance score and metrics for a specific (target, acquisition_method) pair.
    """
    target: str
    acquisition_method: str
    sample_size: int = 0
    successful_acquisitions: int = 0
    validated_results: int = 0
    success_rate: float = 0.0
    validation_rate: float = 0.0
    average_latency_ms: float = 0.0
    total_cost: float = 0.0
    cost_per_validated_result: float = 0.0
    raw_score: float = 0.0
    confidence: float = 0.0
    final_score: float = 0.0
    status: str = "UNSEEN"  # "RANKED" or "UNSEEN"

    @property
    def score(self) -> float:
        """Alias for final_score as specified in prompt requirements."""
        return self.final_score

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["score"] = self.score
        return d

