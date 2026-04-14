"""health.py — Score santé plan de repas (OMS/ANSES). Fusionne : health_score_engine"""
from __future__ import annotations

def health_score(nutrition_totals: dict, n_meals: int = 14) -> dict:
    """Score santé 0-10 basé sur les moyennes journalières d'un plan de repas."""
    n_days = max(n_meals / 2, 1)
    cal  = (nutrition_totals.get("calories", 0) or 0) / n_days
    prot = (nutrition_totals.get("protein",  0) or 0) / n_days
    carb = (nutrition_totals.get("carbs",    0) or 0) / n_days
    fat  = (nutrition_totals.get("fat",      0) or 0) / n_days
    fib  = (nutrition_totals.get("fiber",    0) or 0) / n_days

    def _window(v, lo, hi, spread, pts):
        if lo <= v <= hi: return pts
        if v < lo * 0.6 or v > hi * 1.4: return 0.0
        return max(0.0, pts - min(abs(v - lo), abs(v - hi)) / spread)

    score = (
        _window(cal,  1600, 2500, 400,  2.0) +
        _window(prot,   50,   80,  25,  2.0) +
        _window(fat,    55,   80,  30,  2.0) +
        _window(carb,  225,  325, 100,  2.0) +
        (2.0 if fib >= 25 else (1.0 + (fib-15)/10 if fib >= 15 else max(0.0, fib/15)))
    )
    return {
        "health_score": round(score, 2),
        "max_score": 10.0,
        "averages_per_day": {
            "calories": round(cal), "protein": round(prot,1),
            "carbs": round(carb,1), "fat": round(fat,1), "fiber": round(fib,1),
        },
    }
