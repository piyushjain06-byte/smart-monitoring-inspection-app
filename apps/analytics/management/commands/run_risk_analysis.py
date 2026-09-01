"""
python manage.py run_risk_analysis [--institute <id>]

CLI equivalent of POST /api/analytics/run/ — useful for a cron job or a
`while true; do ...; sleep 3600; done` loop until Celery + Redis are wired
up (see the commented-out block in requirements.txt / config/celery.py).
"""
from django.core.management.base import BaseCommand

from apps.analytics.services.risk_engine import run_risk_engine
from apps.registry.models import Institute


class Command(BaseCommand):
    help = "Runs the Phase 9 risk engine (rule-based score + anomaly detection) for active institutes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--institute", type=int, default=None,
            help="Limit the run to a single institute's id. Omit to score every active institute.",
        )
        parser.add_argument(
            "--no-alerts", action="store_true",
            help="Compute and save RiskSnapshots but don't open any AIAlerts.",
        )

    def handle(self, *args, **options):
        institutes = Institute.objects.filter(is_active=True)
        if options["institute"]:
            institutes = institutes.filter(id=options["institute"])

        institutes = list(institutes)
        if not institutes:
            self.stdout.write(self.style.WARNING("No active institutes matched — nothing to score."))
            return

        results = run_risk_engine(institutes=institutes, create_alerts=not options["no_alerts"])

        for r in results:
            institute = next(i for i in institutes if i.id == r["institute_id"])
            self.stdout.write(f"{institute.name}: {r['score']}/100 ({r['severity']})"
                               + (f" — {r['alerts_created']} new alert(s)" if r["alerts_created"] else ""))

        high_risk = sum(1 for r in results if r["severity"] == "HIGH")
        self.stdout.write(self.style.SUCCESS(
            f"Scored {len(results)} institute(s) — {high_risk} HIGH risk."
        ))
