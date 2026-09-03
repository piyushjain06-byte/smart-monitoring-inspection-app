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
from apps.core.permissions import IsOfficial, is_official

from .models import InspectionReport, InspectionAssignment, Evidence, InspectionTemplate, InspectionField
from .serializers import (
    AutoAssignRequestSerializer,
    InspectionAssignmentSerializer,
    InspectionFieldSerializer,
    InspectionReportSerializer,
    InspectionReportCreateSerializer,
    InspectionTemplateSerializer,
)
from .services import auto_assign, run_auto_assignment, select_surprise_institute


class InspectionTemplateViewSet(viewsets.ModelViewSet):
    """
    Read: any authenticated user — field officers still need this to pick a
    template when submitting (unchanged behaviour from before this file was
    updated). They only ever see is_active=True templates.
    Write (create/update/delete): officials only — this is the frontend
    equivalent of admin.py's InspectionTemplateAdmin, used by
    frontend/src/pages/admin/InspectionTemplates.jsx.
    """
    serializer_class = InspectionTemplateSerializer

    def get_queryset(self):
        qs = InspectionTemplate.objects.all().prefetch_related("fields")
        if not is_official(self.request.user):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsOfficial()]


class InspectionFieldViewSet(viewsets.ModelViewSet):
    """
    CRUD for checklist questions belonging to a template — officials only.
    Supports ?template=<id> to scope to one template's fields, used by the
    template builder page to add/edit/reorder/delete questions.
    """
    queryset = InspectionField.objects.all()
    serializer_class = InspectionFieldSerializer
    permission_classes = [IsOfficial]

    def get_queryset(self):
        qs = super().get_queryset()
        template_id = self.request.query_params.get("template")
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs


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

        if "institute" not in data:
            result = run_auto_assignment(radius_km=data.get("radius_km"))
            return Response({
                "evaluated": result["evaluated"], "assigned": result["assigned"], "skipped": result["skipped"],
                "assignments": InspectionAssignmentSerializer(result["assignments"], many=True).data,
            }, status=status.HTTP_201_CREATED)

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
    """
    Field officers: see only their own submitted reports (unchanged).
    Officials: can now also list/retrieve any report in scope, filtered by
    ?institute=<id> — this is what powers the new report viewer page
    (frontend/src/pages/ReportDetail.jsx), since previously there was no
    way to see a report's answers/evidence without exporting the PDF.
    """
    queryset = InspectionReport.objects.all().select_related(
        "assignment__institute", "assignment__officer", "assignment__template"
    ).prefetch_related("assignment__template__fields", "evidence_items")
    serializer_class = InspectionReportSerializer
    permission_classes = [IsAuthenticated]

    def _scoped_queryset(self, request):
        qs = self.queryset
        if is_official(request.user):
            institute_id = request.query_params.get("institute")
            if institute_id:
                qs = qs.filter(assignment__institute_id=institute_id)
            return qs
        return qs.filter(assignment__officer=request.user)

    def list(self, request):
        qs = self._scoped_queryset(request)
        serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self._scoped_queryset(request), pk=pk)
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
        # Export a PDF report using a simple HTML template + WeasyPrint.
        # Now available to officials too, not just the submitting officer.
        report = get_object_or_404(self._scoped_queryset(request), pk=pk)
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
