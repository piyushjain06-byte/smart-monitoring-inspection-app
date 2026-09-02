import csv

from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.geo import is_within_radius
from apps.core.permissions import IsOfficial

from .models import InspectionReport, InspectionAssignment, Evidence, InspectionTemplate, InspectionField
from .serializers import (
    AutoAssignRequestSerializer,
    InspectionAssignmentSerializer,
    InspectionReportSerializer,
    InspectionReportCreateSerializer,
    InspectionTemplateSerializer,
)
from .services import auto_assign, select_surprise_institute


class InspectionTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InspectionTemplate.objects.filter(is_active=True)
    serializer_class = InspectionTemplateSerializer
    permission_classes = [IsAuthenticated]


class InspectionAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only, official-facing view of assignment history — separate from
    InspectionReportViewSet, which is scoped to "my own" reports for
    inspectors. Powers the institute detail page on the government dashboard.
    Supports ?institute=<id>.
    """
    queryset = InspectionAssignment.objects.select_related("officer", "institute", "template").all()
    serializer_class = InspectionAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_official
        qs = super().get_queryset()
        user = self.request.user
        if not is_official(user):
            # Field officers only ever see their own assignments here.
            qs = qs.filter(officer=user)
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        return qs.order_by("-assigned_at")

    def _require_official(self, request):
        from apps.core.permissions import is_official
        if not is_official(request.user):
            return Response({"detail": "Only officials can assign inspections."}, status=status.HTTP_403_FORBIDDEN)
        return None

    @action(detail=False, methods=["post"], url_path="auto-assign")
    def auto_assign_action(self, request):
        """
        POST /api/inspections/assignments/auto-assign/
        Body: {"institute": <id>, "template": <id, optional>, "due_in_days": <int, optional>}
        Implements plan section 12/13 — official clicks "Assign Inspection",
        backend picks the best officer by distance + workload.
        """
        denied = self._require_official(request)
        if denied:
            return denied

        serializer = AutoAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assignment, breakdown = auto_assign(
                institute=data["institute"],
                template=data.get("template"),
                due_in_days=data.get("due_in_days", 7),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "assignment": InspectionAssignmentSerializer(assignment).data,
            "candidates": breakdown,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="surprise")
    def surprise_action(self, request):
        """
        POST /api/inspections/assignments/surprise/
        Plan section 14 — "Surprise Inspection": randomly picks an active
        institute (weighted towards ones never/overdue inspected) and
        auto-assigns the best available officer to it.
        """
        denied = self._require_official(request)
        if denied:
            return denied

        institute = select_surprise_institute()
        if institute is None:
            return Response({"detail": "No active institutes to inspect."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment, breakdown = auto_assign(institute=institute)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "assignment": InspectionAssignmentSerializer(assignment).data,
            "candidates": breakdown,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        GET /api/inspections/assignments/export-csv/?institute=<id optional>
        Same scoping/filters as the normal list endpoint (officials see
        everything in scope; field officers only their own). Plain CSV,
        no new dependencies — see README's "Good next tasks" list.
        """
        qs = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=inspections.csv"
        writer = csv.writer(response)
        writer.writerow(["Institute", "Officer", "Template", "Assigned At", "Due Date", "Status"])
        for a in qs:
            writer.writerow([
                a.institute.name,
                a.officer.get_full_name() or a.officer.username,
                a.template.name,
                a.assigned_at,
                a.due_date,
                a.status,
            ])
        return response


class InspectionReportViewSet(viewsets.GenericViewSet):
    queryset = InspectionReport.objects.all().select_related("assignment__institute")
    serializer_class = InspectionReportSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        qs = self.queryset.filter(assignment__officer=request.user)
        serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.queryset, pk=pk, assignment__officer=request.user)
        serializer = self.serializer_class(obj)
        return Response(serializer.data)

    def create(self, request):
        serializer = InspectionReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assignment: InspectionAssignment = data["assignment"]
        # Basic ownership check: only the assigned officer can submit
        if assignment.officer != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        # Create report
        report = InspectionReport.objects.create(
            assignment=assignment,
            submitted_latitude=data.get("submitted_latitude"),
            submitted_longitude=data.get("submitted_longitude"),
            answers=data.get("answers", {}),
            notes=data.get("notes", ""),
        )

        # Geofence check
        inst = assignment.institute
        report.location_verified = is_within_radius(
            report.submitted_latitude, report.submitted_longitude,
            inst.latitude, inst.longitude,
        )

        # Compute overall score (simple heuristic)
        try:
            fields = list(InspectionField.objects.filter(template=assignment.template))
            if fields:
                total = 0
                for f in fields:
                    ans = report.answers.get(str(f.id))
                    if f.field_type == InspectionField.FieldType.YES_NO:
                        score = 100 if str(ans).strip().lower() in ("yes", "true", "1") else 0
                    elif f.field_type == InspectionField.FieldType.RATING:
                        try:
                            r = float(ans)
                            score = max(0.0, min(100.0, (r / 5.0) * 100.0))
                        except Exception:
                            score = 0
                    else:
                        # TEXT / TEXTAREA / NUMBER
                        if f.is_required and (ans is None or str(ans).strip() == ""):
                            score = 0
                        else:
                            score = 100
                    total += score
                report.overall_score = int(total / len(fields))
        except Exception:
            report.overall_score = None

        report.save()

        # Save evidence files
        files = request.FILES.getlist("evidence")
        for f in files:
            Evidence.objects.create(report=report, file=f)

        # Mark assignment submitted
        assignment.status = InspectionAssignment.Status.SUBMITTED
        assignment.save()

        out = self.serializer_class(report)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="assignments")
    def assignments(self, request):
        # Return pending assignments for the logged-in officer
        user = request.user
        assignments = (
            InspectionAssignment.objects.filter(officer=user, status=InspectionAssignment.Status.PENDING)
            .select_related("institute", "template")
        )
        data = [
            {
                "id": a.id,
                "institute": a.institute.name,
                "template": a.template.name,
                "due_date": a.due_date,
            }
            for a in assignments
        ]
        return Response(data)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        # Export a PDF report using a simple HTML template + WeasyPrint
        report = get_object_or_404(self.queryset, pk=pk, assignment__officer=request.user)
        html = render_to_string("inspections/report.html", {"report": report})

        try:
            from weasyprint import HTML

            pdf = HTML(string=html).write_pdf()
            resp = HttpResponse(pdf, content_type="application/pdf")
            resp["Content-Disposition"] = f"attachment; filename=report-{report.pk}.pdf"
            return resp
        except Exception:
            return HttpResponse(html)


@login_required
def submit_page(request):
    return render(request, 'inspections/submit.html')
