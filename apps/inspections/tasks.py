from celery import shared_task


@shared_task
def auto_assign_inspections_task(radius_km=None, due_in_hours=None):
    from .services import run_auto_assignment

    result = run_auto_assignment(radius_km=radius_km, due_in_hours=due_in_hours)
    result.pop("assignments", None)
    return result
