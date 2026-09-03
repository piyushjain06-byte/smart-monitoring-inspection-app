from django.core.management.base import BaseCommand

from apps.inspections.services import run_auto_assignment


class Command(BaseCommand):
    help = "Automatically assign surprise inspections to nearby, non-conflicted officers."

    def add_arguments(self, parser):
        parser.add_argument("--radius-km", type=float, default=None)
        parser.add_argument("--due-in-hours", type=float, default=None)

    def handle(self, *args, **options):
        result = run_auto_assignment(
            radius_km=options["radius_km"],
            due_in_hours=options["due_in_hours"],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Evaluated {result['evaluated']} institute(s): "
            f"{result['assigned']} assigned, {result['skipped']} skipped."
        ))
