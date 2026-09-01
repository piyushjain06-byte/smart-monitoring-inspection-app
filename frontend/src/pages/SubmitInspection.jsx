import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";

export default function SubmitInspection() {
  const { id } = useParams();

  const [assignment, setAssignment] = useState(null);
  const [template, setTemplate] = useState(null);
  const [answers, setAnswers] = useState({});
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);

  const [loadError, setLoadError] = useState("");
  const [status, setStatus] = useState(""); // free-text progress message
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    client
      .get(`/inspections/assignments/${id}/`)
      .then(({ data }) => {
        setAssignment(data);
        return client.get(`/inspections/templates/${data.template}/`);
      })
      .then(({ data }) => setTemplate(data))
      .catch(() => setLoadError("Could not load this assignment. It may not be assigned to you."));
  }, [id]);

  function handleAnswerChange(fieldId, value) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
  }

  function handleFilesChange(e) {
    const selected = Array.from(e.target.files);
    setFiles(selected);
    setPreviews(
      selected.map((file) =>
        file.type.startsWith("image/") ? { name: file.name, url: URL.createObjectURL(file) } : { name: file.name, url: null }
      )
    );
  }

  function renderField(field) {
    const value = answers[field.id] ?? "";
    const label = (
      <label className="block text-sm font-medium mb-1">
        {field.label}
        {field.is_required && <span className="text-[var(--danger)]"> *</span>}
      </label>
    );

    if (field.field_type === "YES_NO") {
      return (
        <div key={field.id} className="mb-4">
          {label}
          <select
            className="w-full border border-[var(--line)] px-3 py-2 text-sm"
            value={value}
            onChange={(e) => handleAnswerChange(field.id, e.target.value)}
          >
            <option value="">--</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </div>
      );
    }
    if (field.field_type === "RATING") {
      return (
        <div key={field.id} className="mb-4">
          {label}
          <input
            type="number"
            min={1}
            max={5}
            className="w-full border border-[var(--line)] px-3 py-2 text-sm"
            value={value}
            onChange={(e) => handleAnswerChange(field.id, e.target.value)}
          />
        </div>
      );
    }
    if (field.field_type === "TEXTAREA") {
      return (
        <div key={field.id} className="mb-4">
          {label}
          <textarea
            rows={3}
            className="w-full border border-[var(--line)] px-3 py-2 text-sm"
            value={value}
            onChange={(e) => handleAnswerChange(field.id, e.target.value)}
          />
        </div>
      );
    }
    return (
      <div key={field.id} className="mb-4">
        {label}
        <input
          type={field.field_type === "NUMBER" ? "number" : "text"}
          className="w-full border border-[var(--line)] px-3 py-2 text-sm"
          value={value}
          onChange={(e) => handleAnswerChange(field.id, e.target.value)}
        />
      </div>
    );
  }

  function handleSubmit() {
    setSubmitError("");
    if (!navigator.geolocation) {
      setSubmitError("Geolocation isn't supported on this device/browser — required to verify you're on-site.");
      return;
    }
    setStatus("Getting your location…");
    setSubmitting(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => doSubmit(pos.coords.latitude, pos.coords.longitude),
      (err) => {
        setSubmitting(false);
        setSubmitError(`Could not get your location: ${err.message}`);
      }
    );
  }

  async function doSubmit(lat, lon) {
    setStatus("Uploading…");
    const fd = new FormData();
    fd.append("assignment", id);
    fd.append("submitted_latitude", lat);
    fd.append("submitted_longitude", lon);
    fd.append("notes", notes);
    fd.append("answers", JSON.stringify(answers));
    files.forEach((f) => fd.append("evidence", f));

    try {
      await client.post("/inspections/reports/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (evt.total) setUploadPct(Math.round((evt.loaded / evt.total) * 100));
        },
      });
      setStatus("Submitted successfully.");
      setDone(true);
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.data || "Submission failed.";
      setSubmitError(typeof detail === "string" ? detail : JSON.stringify(detail));
      setStatus("");
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className="p-8">
        <p className="text-sm text-[var(--danger)]">{loadError}</p>
        <Link to="/inspector" className="text-sm text-[var(--accent)] underline">
          Back to my assignments
        </Link>
      </div>
    );
  }

  if (!assignment || !template) {
    return <div className="p-8 text-sm text-[var(--ink-soft)]">Loading…</div>;
  }

  if (done) {
    return (
      <div className="p-8 max-w-lg">
        <div className="bg-white border border-[var(--ok)] px-4 py-4 text-sm text-[var(--ok)]">
          Inspection submitted for <strong>{assignment.institute_name}</strong>.
        </div>
        <Link to="/inspector" className="inline-block mt-4 text-sm text-[var(--accent)] underline">
          Back to my assignments
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-lg space-y-5">
      <div>
        <Link to="/inspector" className="text-xs text-[var(--accent)] underline">
          ← Back to my assignments
        </Link>
        <h1 className="text-lg font-semibold text-[var(--ink)] mt-2">{assignment.institute_name}</h1>
        <p className="text-sm text-[var(--ink-soft)]">
          {template.name} · due {assignment.due_date}
        </p>
      </div>

      <div className="bg-white border border-[var(--line)] p-5 space-y-1">
        {template.fields
          .slice()
          .sort((a, b) => a.order - b.order)
          .map(renderField)}

        <div className="mb-2">
          <label className="block text-sm font-medium mb-1">Additional notes</label>
          <textarea
            rows={2}
            className="w-full border border-[var(--line)] px-3 py-2 text-sm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        <div className="mb-2">
          <label className="block text-sm font-medium mb-1">Evidence photos/videos</label>
          <input
            type="file"
            multiple
            accept="image/*,video/*"
            capture="environment"
            onChange={handleFilesChange}
            className="text-sm"
          />
          {previews.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {previews.map((p, idx) =>
                p.url ? (
                  <img
                    key={idx}
                    src={p.url}
                    alt={p.name}
                    className="w-20 h-16 object-cover border border-[var(--line)]"
                  />
                ) : (
                  <div
                    key={idx}
                    className="w-20 h-16 border border-[var(--line)] text-[10px] text-[var(--ink-soft)] flex items-center justify-center text-center px-1"
                  >
                    {p.name}
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </div>

      {submitError && <p className="text-sm text-[var(--danger)]">{submitError}</p>}
      {status && !submitError && <p className="text-sm text-[var(--ink-soft)]">{status}</p>}
      {submitting && uploadPct > 0 && (
        <div className="w-full h-1.5 bg-[var(--line)]">
          <div className="h-1.5 bg-[var(--accent)]" style={{ width: `${uploadPct}%` }} />
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
      >
        {submitting ? "Submitting…" : "Get Location & Submit"}
      </button>
    </div>
  );
}
