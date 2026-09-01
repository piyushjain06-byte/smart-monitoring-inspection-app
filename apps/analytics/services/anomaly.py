"""
Phase 9, Part 23 — AI Anomaly Detection.

    "Start with a simple ML model. Use: Scikit-learn Isolation Forest."

Isolation Forest needs a reasonable number of samples to say anything
meaningful about "unusual vs. the rest" — with only 1-2 institutes in the
DB (a fresh dev install), every institute is trivially "normal" or the
model itself isn't well-defined. Rather than fabricate a result, this
degrades to "no institute flagged, insufficient data" below
MIN_INSTITUTES_FOR_ANOMALY, same pattern as
apps.inspections.services.select_inspector_for_institute() returning
(None, []) when there's nobody eligible.
"""
from apps.registry.models import Institute

MIN_INSTITUTES_FOR_ANOMALY = 5

# Feature order matters — must match how each row is built below.
FEATURE_NAMES = [
    "attendance_rate",
    "camera_online_ratio",
    "latest_inspection_score_normalized",
    "inspection_frequency",
    "recent_high_alerts",
]

# Used when a feature is None (missing data) for one institute — the
# "everything is fine" value for that signal, so a missing feature never
# itself looks anomalous. Isolation Forest still gets to compare institutes
# on whichever signals they DO have data for.
NEUTRAL_DEFAULTS = {
    "attendance_rate": 1.0,
    "camera_online_ratio": 1.0,
    "latest_inspection_score_normalized": 1.0,
    "inspection_frequency": 0,
    "recent_high_alerts": 0,
}


def _feature_row(features: dict) -> list:
    normalized_score = (
        features["latest_inspection_score"] / 100.0 if features["latest_inspection_score"] is not None else None
    )
    raw = {
        "attendance_rate": features["attendance_rate"],
        "camera_online_ratio": features["camera_online_ratio"],
        "latest_inspection_score_normalized": normalized_score,
        "inspection_frequency": features["inspection_frequency"],
        "recent_high_alerts": features["recent_high_alerts"],
    }
    return [raw[name] if raw[name] is not None else NEUTRAL_DEFAULTS[name] for name in FEATURE_NAMES]


def detect_anomalies(features_by_institute: dict) -> dict:
    """
    features_by_institute: {institute_id: features_dict} (see features.collect_features).
    Returns {institute_id: {"is_anomaly": bool, "anomaly_score": float | None}}.
    """
    institute_ids = list(features_by_institute.keys())
    result = {iid: {"is_anomaly": False, "anomaly_score": None} for iid in institute_ids}

    if len(institute_ids) < MIN_INSTITUTES_FOR_ANOMALY:
        return result

    from sklearn.ensemble import IsolationForest

    matrix = [_feature_row(features_by_institute[iid]) for iid in institute_ids]

    model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
    predictions = model.fit_predict(matrix)  # -1 = anomaly, 1 = normal
    scores = model.decision_function(matrix)  # lower = more anomalous

    for iid, prediction, score in zip(institute_ids, predictions, scores):
        result[iid] = {"is_anomaly": bool(prediction == -1), "anomaly_score": round(float(score), 4)}
    return result


def detect_anomalies_for_all_active() -> dict:
    """Convenience wrapper: runs detect_anomalies() over every active institute."""
    from .features import collect_features

    institutes = Institute.objects.filter(is_active=True)
    features_by_institute = {inst.id: collect_features(inst) for inst in institutes}
    return detect_anomalies(features_by_institute)
