"""
Canonical score dimension keys used throughout MIRU.
These map directly to Japanese HR evaluation criteria and the frontend radar chart.
"""

SCORE_DIMENSIONS = [
    "wa_teamwork",         # 協調性 — group harmony, team-first language
    "loyalty_commitment",  # 忠誠心 — long-term signals, no job-hopping language
    "humility",            # 謙虚さ — self-presentation without arrogance
    "kaizen_growth",       # 成長意欲 — growth framed within company, not personal ambition
    "cultural_fit",        # 文化適合 — Japanese business etiquette, format compliance
]

DEFAULT_SCORES = {dim: 5 for dim in SCORE_DIMENSIONS}
