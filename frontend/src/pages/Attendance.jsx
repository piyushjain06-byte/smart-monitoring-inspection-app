import { useEffect, useMemo, useState } from "react";
import { client, downloadBlob } from "../api/client";

const STATUS_STYLE = {
  PRESENT: "text-[var(--ok)]",
  LATE: "text-[var(--warn)]",
  ABSENT: "text-[var(--danger)]",
  HALF_DAY: "text-[var(--ink-soft)]",
};

export default function Attendance() {
  const [records, setRecords] = useState([]);
  const [staff, setStaff] = useState([]);
  const [institutes, setInstitutes] = useState([]);
  const [selectedInstitute, setSelectedInstitute] = useState("");
  const [selectedStaff, setSelectedStaff] = useState("");
  const [status, setStatus] = useState("PRESENT");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  function loadData() {
    setLoading(true);
    Promise.all([
      client.get("/attendance/records/"),
      client.get("/registry/staff/"),
      client.get("/registry/institutes/"),
    ])
      .then(([attendanceRes, staffRes, instituteRes]) => {
        setRecords(attendanceRes.data);
        setStaff(staffRes.data);
        setInstitutes(instituteRes.data);
        if (!selectedInstitute && instituteRes.data.length) {
          setSelectedInstitute(String(instituteRes.data[0].id));
        }
      })
      .catch(() => setError("Could not load attendance data. Is the Django server running?"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadData();
  }, []);

  const filteredStaff = useMemo(() => {
    if (!selectedInstitute) return [];
    return staff.filter((member) => String(member.institute) === String(selectedInstitute));
  }, [selectedInstitute, staff]);

  useEffect(() => {
    if (filteredStaff.length > 0 && !filteredStaff.some((member) => String(member.id) === String(selectedStaff))) {
      setSelectedStaff(String(filteredStaff[0].id));
    }
  }, [filteredStaff, selectedStaff]);

  async function handleMark(action) {
    if (!selectedInstitute || !selectedStaff) {
      setError("Please select an institute and a staff member first.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      await client.post(`/attendance/records/${action}/`, {
        institute_id: Number(selectedInstitute),
        staff_id: Number(selectedStaff),
        status,
        notes,
      });
      setNotes("");
      loadData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || "Could not update attendance.";
      setError(detail);
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    setError("");
    try {
      await downloadBlob("/attendance/records/export-csv/", "attendance.csv");
    } catch {
      setError("Could not export attendance records.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="p-8 space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--ink)]">Attendance</h1>
          <p className="text-sm text-[var(--ink-soft)]">
            Daily staff attendance tracking for each institute.
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="shrink-0 border border-[var(--ink)] text-[var(--ink)] text-sm font-medium px-4 py-2 hover:bg-[var(--ink)] hover:text-white transition-colors disabled:opacity-60"
        >
          {exporting ? "Exporting…" : "Export CSV"}
        </button>
      </header>

      {error && (
        <div className="border border-[var(--danger)] bg-[var(--danger)]/5 text-[var(--danger)] text-sm px-4 py-2">
          {error}
        </div>
      )}

      <section className="bg-white border border-[var(--line)] p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Institute</span>
            <select
              value={selectedInstitute}
              onChange={(e) => setSelectedInstitute(e.target.value)}
              className="w-full border border-[var(--line)] px-3 py-2 bg-white text-[var(--ink)] outline-none"
            >
              <option value="">Select institute</option>
              {institutes.map((institute) => (
                <option key={institute.id} value={institute.id}>{institute.name}</option>
              ))}
            </select>
          </label>

          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Staff</span>
            <select
              value={selectedStaff}
              onChange={(e) => setSelectedStaff(e.target.value)}
              disabled={!filteredStaff.length}
              className="w-full border border-[var(--line)] px-3 py-2 bg-white text-[var(--ink)] outline-none disabled:opacity-50"
            >
              <option value="">Select staff</option>
              {filteredStaff.map((member) => (
                <option key={member.id} value={member.id}>{member.full_name}</option>
              ))}
            </select>
          </label>

          <label className="text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full border border-[var(--line)] px-3 py-2 bg-white text-[var(--ink)] outline-none"
            >
              <option value="PRESENT">Present</option>
              <option value="LATE">Late</option>
              <option value="ABSENT">Absent</option>
              <option value="HALF_DAY">Half day</option>
            </select>
          </label>
        </div>

        <label className="text-sm space-y-1 block">
          <span className="text-[var(--ink-soft)]">Notes</span>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full border border-[var(--line)] px-3 py-2 bg-white text-[var(--ink)] outline-none resize-none"
            placeholder="Optional note about attendance or delay"
          />
        </label>

        <div className="flex gap-3">
          <button
            onClick={() => handleMark("check-in")}
            disabled={saving || !selectedInstitute || !selectedStaff}
            className="bg-[var(--ink)] text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Saving…" : "Check In"}
          </button>
          <button
            onClick={() => handleMark("check-out")}
            disabled={saving || !selectedInstitute || !selectedStaff}
            className="border border-[var(--line)] px-4 py-2 text-sm font-medium text-[var(--ink)] disabled:opacity-50"
          >
            Check Out
          </button>
        </div>
      </section>

      <section className="bg-white border border-[var(--line)]">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-medium">Today’s attendance</div>

        {loading ? (
          <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">Loading…</div>
        ) : records.length === 0 ? (
          <div className="px-4 py-4 text-sm text-[var(--ink-soft)]">No attendance records yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--line)] text-left text-[var(--ink-soft)]">
                <th className="px-4 py-2 font-medium">Staff</th>
                <th className="px-4 py-2 font-medium">Institute</th>
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Check in</th>
                <th className="px-4 py-2 font-medium">Check out</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-[var(--line)] last:border-0">
                  <td className="px-4 py-2.5">{record.staff_name}</td>
                  <td className="px-4 py-2.5">{record.institute_name}</td>
                  <td className="px-4 py-2.5">{record.date}</td>
                  <td className="px-4 py-2.5">{record.check_in ? new Date(record.check_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                  <td className="px-4 py-2.5">{record.check_out ? new Date(record.check_out).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                  <td className={`px-4 py-2.5 ${STATUS_STYLE[record.status] || ""}`}>{record.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
