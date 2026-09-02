import csv
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsOfficial
from apps.registry.models import Institute, Staff

from .models import AttendanceRecord
from .serializers import AttendanceMarkSerializer, AttendanceRecordSerializer


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related("staff", "institute").all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        institute_id = self.request.query_params.get("institute")
        staff_id = self.request.query_params.get("staff")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        return qs.order_by("-date")

    def create(self, request, *args, **kwargs):
        serializer = AttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        staff = Staff.objects.get(id=data["staff_id"])
        institute = Institute.objects.get(id=data["institute_id"])
        record, created = AttendanceRecord.objects.get_or_create(
            staff=staff,
            institute=institute,
            date=datetime.today().date(),
        )

        record.status = data.get("status", record.status)
        record.notes = data.get("notes", record.notes)
        if not record.check_in:
            record.check_in = datetime.now()
        record.check_out = record.check_out or None
        record.save()

        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        serializer = AttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        staff = Staff.objects.get(id=data["staff_id"])
        institute = Institute.objects.get(id=data["institute_id"])

        record, created = AttendanceRecord.objects.get_or_create(
            staff=staff,
            institute=institute,
            date=datetime.today().date(),
        )
        record.check_in = datetime.now()
        record.status = AttendanceRecord.Status.PRESENT
        record.save()
        return Response({"status": "checked_in", "record": AttendanceRecordSerializer(record).data})

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        serializer = AttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        staff = Staff.objects.get(id=data["staff_id"])
        institute = Institute.objects.get(id=data["institute_id"])

        record = AttendanceRecord.objects.filter(
            staff=staff,
            institute=institute,
            date=datetime.today().date(),
        ).first()

        if not record:
            return Response({"detail": "No check-in record found."}, status=status.HTTP_400_BAD_REQUEST)

        record.check_out = datetime.now()
        record.save()
        return Response({"status": "checked_out", "record": AttendanceRecordSerializer(record).data})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = AttendanceRecord.objects.all()
        institute_id = request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)

        total = qs.count()
        present = qs.filter(status=AttendanceRecord.Status.PRESENT).count()
        late = qs.filter(status=AttendanceRecord.Status.LATE).count()
        absent = qs.filter(status=AttendanceRecord.Status.ABSENT).count()

        return Response({
            "total": total,
            "present": present,
            "late": late,
            "absent": absent,
        })

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        GET /api/attendance/records/export-csv/?institute=<id optional>
        Same ?institute=/?staff= filters as the normal list endpoint. Plain
        CSV, no new dependencies — see README's "Good next tasks" list.
        """
        qs = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=attendance.csv"
        writer = csv.writer(response)
        writer.writerow(["Staff", "Institute", "Date", "Check In", "Check Out", "Status", "Notes"])
        for record in qs:
            writer.writerow([
                record.staff.full_name, record.institute.name, record.date,
                record.check_in, record.check_out, record.status, record.notes,
            ])
        return response
