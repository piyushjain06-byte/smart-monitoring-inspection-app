"""
Phase 3 (backend) — Automatic Inspection Assignment.

Implements the plan's "Assignment Algorithm" (section 13) as literally as
possible, on purpose kept simple per the plan's own instruction ("Start
simple... Later you can make this an optimization/AI system"):

    1. Get pending inspections           -> caller passes the institute
    2. Get available inspectors          -> _eligible_officers()
    3. Calculate distance                -> apps.core.geo.distance_meters()
    4. Check inspector workload          -> current PENDING assignment count
    5. Check project priority            -> handled by select_surprise_institute()
    6. Select best inspector             -> select_inspector_for_institute()
    7. Create assignment                 -> auto_assign()
"""
import random
import uuid
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.core.geo import distance_meters
from apps.registry.models import Institute

from .models import InspectionAssignment, InspectionTemplate

logger = logging.getLogger(__name__)

# Officers at or above this many PENDING assignments are deprioritised
# (not excluded outright — better to give someone a 6th job than leave an
# institute completely unassigned if every officer is already busy).
WORKLOAD_SOFT_CAP = 5

# Weight applied to workload in the scoring formula. Kept as one named
# constant so it's obvious where to tune it: "1 pending inspection" is
# currently treated as being as undesirable as ~15 km of extra travel.
WORKLOAD_PENALTY_KM_EQUIVALENT = 15
ANTI_COLLUSION_DAYS = 180


def _eligible_officers():
    """Active users who actually do field work (Part 4.1's is_field_role)."""
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    return UserModel.objects.filter(
        role__in=["INSPECTION_OFFICER", "PMU_TEAM"],
        is_active=True,
        base_latitude__isnull=False,
        base_longitude__isnull=False,
    )


def eligible_officers_for_institute(institute, scheduled_at=None, radius_km=None):
    """Return officers passing proximity, same-day workload, and anti-collusion checks."""
    if institute.latitude is None or institute.longitude is None:
        return []
    scheduled_at = scheduled_at or (timezone.now() + timedelta(hours=3))
    radius_km = radius_km or getattr(settings, "AUTO_ASSIGN_RADIUS_KM", 50)
    scheduled_date = timezone.localtime(scheduled_at).date()
    cutoff = timezone.now() - timedelta(days=ANTI_COLLUSION_DAYS)
    eligible = []
    for officer in _eligible_officers():
        distance_km = distance_meters(
            officer.base_latitude, officer.base_longitude,
            institute.latitude, institute.longitude,
        ) / 1000.0
        if distance_km > radius_km:
            continue
        if InspectionAssignment.objects.filter(
            officer=officer, status=InspectionAssignment.Status.PENDING,
            due_date=scheduled_date,
        ).exists():
            continue
        # FLATTENED ARCHITECTURE: this used to key off institute__ngo_id
        # (don't send the same officer back to an institute run by the same
        # NGO too often). Institute no longer has an `ngo` field — Scheme is
        # now the closest shared attribute between institutes, so the
        # anti-collusion window is keyed off Scheme instead.
        if InspectionAssignment.objects.filter(
            officer=officer, institute__scheme_id=institute.scheme_id,
            assigned_at__gte=cutoff,
        ).exists():
            continue
        eligible.append((officer, distance_km))
    return eligible


def score_officers_for_institute(institute: Institute):
    """
    Returns a list of dicts, one per eligible officer, each with the raw
    inputs and the final score — sorted best (lowest score) first. Kept as
    its own function so the API can return the full breakdown, mirroring
    the plan's demo:
        Inspector 23 -> 4 km
        Inspector 12 -> 25 km
        Inspector 07 -> 11 km
        -> Inspector 23 selected
    """
    breakdown = []
    for officer in _eligible_officers():
        workload = InspectionAssignment.objects.filter(
            officer=officer, status=InspectionAssignment.Status.PENDING
        ).count()

        if officer.base_latitude is not None and officer.base_longitude is not None and \
           institute.latitude is not None and institute.longitude is not None:
            distance_km = distance_meters(
                officer.base_latitude, officer.base_longitude,
                institute.latitude, institute.longitude,
            ) / 1000.0
        else:
            # No known location for this officer or institute — don't crash
            # the whole engine over one missing coordinate, just penalise it
            # heavily so an officer *with* a known location wins when one exists.
            distance_km = None

        effective_distance = distance_km if distance_km is not None else 999.0
        score = effective_distance + (workload * WORKLOAD_PENALTY_KM_EQUIVALENT)

        breakdown.append({
            "officer_id": officer.id,
            "officer_name": officer.get_full_name() or officer.username,
            "distance_km": round(distance_km, 1) if distance_km is not None else None,
            "workload": workload,
            "score": round(score, 1),
        })

    breakdown.sort(key=lambda row: row["score"])
    return breakdown


def select_inspector_for_institute(institute: Institute):
    """Returns (officer, breakdown) — officer is None if nobody is eligible."""
    from django.contrib.auth import get_user_model

    breakdown = score_officers_for_institute(institute)
    if not breakdown:
        return None, breakdown

    best = breakdown[0]
    UserModel = get_user_model()
    officer = UserModel.objects.get(id=best["officer_id"])
    return officer, breakdown


def auto_assign(institute: Institute, template: InspectionTemplate = None, due_in_days: int = 7):
    """
    Creates and returns an InspectionAssignment for `institute`, choosing the
    best available officer. Raises ValueError if there's no eligible officer
    or no active template to assign.
    """
    if template is None:
        template = InspectionTemplate.objects.filter(is_active=True).first()
    if template is None:
        raise ValueError("No active inspection template exists — create one in /admin/ first.")

    officer, breakdown = select_inspector_for_institute(institute)
    if officer is None:
        raise ValueError("No active Inspection Officer / PMU Team accounts exist to assign to.")

    assignment = InspectionAssignment.objects.create(
        officer=officer,
        institute=institute,
        template=template,
        due_date=timezone.now().date() + timedelta(days=due_in_days),
        random_seed=uuid.uuid4().hex,
        weight_snapshot=breakdown,
    )
    return assignment, breakdown


def _priority_institutes():
    """Find high-risk or overdue institutes without pending work."""
    from apps.analytics.models import RiskSnapshot

    high_risk_ids = set()
    for institute_id in RiskSnapshot.objects.filter(
        institute__is_active=True,
    ).values_list("institute_id", flat=True).distinct():
        latest = RiskSnapshot.objects.filter(institute_id=institute_id).first()
        if latest and latest.severity in {"HIGH", "CRITICAL"}:
            high_risk_ids.add(institute_id)
    overdue_ids = set(InspectionAssignment.objects.filter(
        status=InspectionAssignment.Status.OVERDUE,
        institute__is_active=True,
    ).values_list("institute_id", flat=True))
    pending_ids = InspectionAssignment.objects.filter(
        status=InspectionAssignment.Status.PENDING,
    ).values("institute_id")
    return Institute.objects.filter(
        is_active=True, id__in=high_risk_ids | overdue_ids,
    ).exclude(id__in=pending_ids).order_by("id")


def notify_assignment_created(assignment):
    """Best-effort inspector notification through the existing Channels layer."""
    logger.info(
        "Surprise inspection assigned: assignment=%s officer=%s institute=%s scheduled_at=%s",
        assignment.id, assignment.officer_id, assignment.institute_id, assignment.scheduled_at,
    )
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from apps.analytics.consumers import ALERTS_GROUP

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                ALERTS_GROUP,
                {
                    "type": "assignment.created",
                    "assignment_id": assignment.id,
                    "officer_id": assignment.officer_id,
                    "institute_id": assignment.institute_id,
                    "scheduled_at": assignment.scheduled_at.isoformat(),
                },
            )
    except Exception:
        pass


def run_auto_assignment(radius_km=None, due_in_hours=None, institute_ids=None):
    """Create random surprise assignments for all eligible priority institutes."""
    template = InspectionTemplate.objects.filter(is_active=True).first()
    institutes = _priority_institutes()
    if institute_ids:
        institutes = institutes.filter(id__in=institute_ids)
    if template is None:
        return {"evaluated": institutes.count(), "assigned": 0, "skipped": institutes.count(), "assignments": []}

    due_in_hours = due_in_hours or getattr(settings, "AUTO_ASSIGN_NOTICE_HOURS", 3)
    scheduled_at = timezone.now() + timedelta(hours=due_in_hours)
    assignments = []
    skipped = 0
    for institute in institutes:
        candidates = eligible_officers_for_institute(institute, scheduled_at, radius_km)
        if not candidates:
            skipped += 1
            continue
        officer, distance_km = random.choice(candidates)
        assignment = InspectionAssignment.objects.create(
            officer=officer, institute=institute, template=template,
            scheduled_at=scheduled_at, due_date=scheduled_at.date(),
            random_seed=uuid.uuid4().hex,
            weight_snapshot={"distance_km": round(distance_km, 2), "radius_km": radius_km or getattr(settings, "AUTO_ASSIGN_RADIUS_KM", 50)},
        )
        notify_assignment_created(assignment)
        assignments.append(assignment)
    return {"evaluated": institutes.count(), "assigned": len(assignments), "skipped": skipped, "assignments": assignments}


def select_surprise_institute():
    """
    Part 14 — Surprise Inspection. Randomly picks an active institute,
    weighted towards ones that most need a fresh look: never inspected, or
    overdue. This is the "project priority" step (section 13, step 5) —
    kept as a simple weighting, not a full risk model (that's Phase 9).
    """
    institutes = list(Institute.objects.filter(is_active=True))
    if not institutes:
        return None

    def priority_weight(inst):
        latest = inst.inspection_assignments.order_by("-assigned_at").first()
        if latest is None:
            return 5  # never inspected — highest priority
        if latest.status == InspectionAssignment.Status.OVERDUE:
            return 4
        if latest.status == InspectionAssignment.Status.PENDING:
            return 1  # already has something in flight — deprioritise
        return 2  # SUBMITTED — eligible again, but not urgently

    weights = [priority_weight(i) for i in institutes]
    return random.choices(institutes, weights=weights, k=1)[0]
