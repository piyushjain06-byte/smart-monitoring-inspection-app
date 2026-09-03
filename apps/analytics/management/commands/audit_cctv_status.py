"""python manage.py audit_cctv_status"""

from django.core.management.base import BaseCommand

from apps.analytics.services.risk_engine import run_risk_engine
from apps.registry.models import Institute


class Command(BaseCommand):
    help = "Audit CCTV heartbeat ages and recalculate active institute risk scores."

    def handle(self, *args, **options):
        institutes = list(Institute.objects.filter(is_active=True))
        results = run_risk_engine(institutes=institutes, create_alerts=True)
        high_risk = sum(result["severity"] == "HIGH" for result in results)
        self.stdout.write(self.style.SUCCESS(
            f"Audited {len(results)} institute(s) — {high_risk} HIGH risk."
        ))