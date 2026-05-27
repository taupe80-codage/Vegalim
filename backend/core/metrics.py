"""
backend/core/metrics.py — Métriques runtime légères pour ALIM v6.

Collecte en mémoire : compteurs de requêtes, latences, erreurs.
Exposé via GET /metrics (format JSON, compatible dashboards simples).

Pas de dépendance externe — si tu veux Prometheus, ajouter prometheus_client
et remplacer _store par un Counter/Histogram Prometheus standard.

Thread-safe via threading.Lock.
"""
import threading
import time
from collections import defaultdict

_lock   = threading.Lock()

_store = {
    "requests_total":    0,       # toutes routes confondues
    "requests_by_route": defaultdict(int),   # route → count
    "errors_total":      0,       # réponses 4xx / 5xx
    "errors_by_status":  defaultdict(int),   # status_code → count
    "latency_sum_ms":    0.0,     # somme des durées (pour moyenne)
    "latency_count":     0,
    "started_at":        time.time(),
}


def record_request(route: str, status_code: int, duration_ms: float) -> None:
    """Appelé par le middleware pour chaque requête terminée."""
    with _lock:
        _store["requests_total"]        += 1
        _store["requests_by_route"][route] += 1
        _store["latency_sum_ms"]        += duration_ms
        _store["latency_count"]         += 1
        if status_code >= 400:
            _store["errors_total"]              += 1
            _store["errors_by_status"][str(status_code)] += 1


def get_metrics() -> dict:
    """Retourne un snapshot des métriques courantes."""
    with _lock:
        count    = _store["latency_count"]
        avg_lat  = (_store["latency_sum_ms"] / count) if count else 0.0
        uptime_s = time.time() - _store["started_at"]

        return {
            "uptime_seconds":    round(uptime_s, 1),
            "requests_total":    _store["requests_total"],
            "requests_per_min":  round(_store["requests_total"] / max(uptime_s / 60, 1), 2),
            "errors_total":      _store["errors_total"],
            "error_rate":        round(
                _store["errors_total"] / max(_store["requests_total"], 1), 4
            ),
            "latency_avg_ms":    round(avg_lat, 2),
            "top_routes":        dict(
                sorted(_store["requests_by_route"].items(),
                       key=lambda x: -x[1])[:10]
            ),
            "errors_by_status":  dict(_store["errors_by_status"]),
        }
