from typing import Any, Dict

from services.score_dimensions import SCORE_DIMENSIONS


def get_radar_chart_data(overall_scores: Dict[str, Any]) -> Dict[str, float]:
    s = overall_scores or {}
    return {dim: float(s.get(dim, 0.0)) for dim in SCORE_DIMENSIONS}


def get_score_summary(overall_scores: Dict[str, Any]) -> Dict[str, float]:
    return {
        "teamwork": float(overall_scores.get("wa_teamwork", 0.0)),
        "commitment": float(overall_scores.get("loyalty_commitment", 0.0)),
        "humility": float(overall_scores.get("humility", 0.0)),
        "growth": float(overall_scores.get("kaizen_growth", 0.0)),
        "cultural_fit": float(overall_scores.get("cultural_fit", 0.0)),
    }
