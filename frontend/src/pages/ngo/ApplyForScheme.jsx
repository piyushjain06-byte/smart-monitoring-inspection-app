import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { client } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const BLANK = {
  scheme: "", organization_name: "", registration_number: "",
  contact_person: "", contact_phone: "", contact_email: "",
  address: "", state: "", district: "", latitude: "", longitude: "",
  project_name: "", project_plan: "", proposed_fund_amount: "",
  proposed_start_date: "", proposed_end_date: "",
};

/**
 * PS 26095 onboarding flow: Scheme Catalogue -> NGO/Institute apply/propose.
 * The applicant's own role (set at /register) decides whether they're
 * applying as an NGO or an Institute — this page doesn't ask again.
 */
export default function ApplyForScheme() {
  const { user } = useAuth();
  const applicantType = user?.role === "PROJECT_INCHARGE" ? "INSTITUTE" : "NGO";
  const [schemes, setSchemes] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    client.get("/onboarding/schemes-catalogue/").then(({ data }) => setSchemes(data));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        ...form,
        applicant_type: applicantType,
        latitude: form.latitude === "" ? null : parseFloat(form.latitude),
        longitude: form.longitude === "" ? null : parseFloat(form.longitude),
        proposed_start_date: form.proposed_start_date || null,
        proposed_end_date: form.proposed_end_date || null,
      };
      await client.post("/onboarding/applications/", payload);
      setDone(true);
    } catch (err) {
      const detail = err.response?.data;
      setError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Could not submit application.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="p-8 max-w-lg">
        <div className="bg-white border border-[var(--ok)] px-4 py-4 text-sm text-[var(--ok)]">
          Application submitted. The DoSJE HQ Super Admin will review your
          plan and funding request — check "My Applications" for status.
        </div>
        <button
          onClick={() => navigate("/ngo-portal/applications")}
          className="inline-block mt-4 text-sm text-[var(--accent)] underline"
        >
          View my applications
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl space-y-4">
      <header>
        <h1 className="text-lg font-semibold text-[var(--ink)]">
          Apply for a Scheme — {applicantType === "NGO" ? "NGO" : "Institute"}
        </h1>
        <p className="text-sm text-[var(--ink-soft)]">
          Pick a government scheme and submit your project plan and funding
          request. A DoSJE HQ Super Admin will review and approve or reject it.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="bg-white border border-[var(--line)] p-5 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">Scheme</span>
          <select required className="w-full border border-[var(--line)] px-3 py-2 bg-white"
            value={form.scheme} onChange={(e) => setForm({ ...form, scheme: e.target.value })}>
            <option value="">--</option>
            {schemes.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>

        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">{applicantType === "NGO" ? "NGO name" : "Institute name"}</span>
          <input required className="w-full border border-[var(--line)] px-3 py-2"
            value={form.organization_name} onChange={(e) => setForm({ ...form, organization_name: e.target.value })} />
        </label>

        {applicantType === "NGO" && (
          <label className="space-y-1">
            <span className="text-[var(--ink-soft)]">NGO registration number</span>
            <input required className="w-full border border-[var(--line)] px-3 py-2"
              value={form.registration_number} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} />
          </label>
        )}
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Contact person</span>
          <input className="w-full border border-[var(--line)] px-3 py-2"
            value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Contact phone</span>
          <input className="w-full border border-[var(--line)] px-3 py-2"
            value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Contact email</span>
          <input type="email" className="w-full border border-[var(--line)] px-3 py-2"
            value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
        </label>

        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">Address</span>
          <input className="w-full border border-[var(--line)] px-3 py-2"
            value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">State{applicantType === "INSTITUTE" && " *"}</span>
          <input required={applicantType === "INSTITUTE"} className="w-full border border-[var(--line)] px-3 py-2"
            value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">District{applicantType === "INSTITUTE" && " *"}</span>
          <input required={applicantType === "INSTITUTE"} className="w-full border border-[var(--line)] px-3 py-2"
            value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Latitude</span>
          <input className="w-full border border-[var(--line)] px-3 py-2"
            value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Longitude</span>
          <input className="w-full border border-[var(--line)] px-3 py-2"
            value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} />
        </label>

        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">Project name</span>
          <input required className="w-full border border-[var(--line)] px-3 py-2"
            value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} />
        </label>
        <label className="md:col-span-2 space-y-1">
          <span className="text-[var(--ink-soft)]">Project plan</span>
          <textarea required rows={5} className="w-full border border-[var(--line)] px-3 py-2"
            value={form.project_plan} onChange={(e) => setForm({ ...form, project_plan: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Proposed fund amount (₹)</span>
          <input required type="number" step="0.01" className="w-full border border-[var(--line)] px-3 py-2"
            value={form.proposed_fund_amount} onChange={(e) => setForm({ ...form, proposed_fund_amount: e.target.value })} />
        </label>
        <div />
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Proposed start date</span>
          <input type="date" className="w-full border border-[var(--line)] px-3 py-2"
            value={form.proposed_start_date} onChange={(e) => setForm({ ...form, proposed_start_date: e.target.value })} />
        </label>
        <label className="space-y-1">
          <span className="text-[var(--ink-soft)]">Proposed end date</span>
          <input type="date" className="w-full border border-[var(--line)] px-3 py-2"
            value={form.proposed_end_date} onChange={(e) => setForm({ ...form, proposed_end_date: e.target.value })} />
        </label>

        {error && <p className="md:col-span-2 text-sm text-[var(--danger)]">{error}</p>}

        <div className="md:col-span-2">
          <button type="submit" disabled={submitting}
            className="bg-[var(--ink)] text-white text-sm font-medium px-4 py-2 hover:bg-[var(--accent)] disabled:opacity-60">
            {submitting ? "Submitting…" : "Submit application"}
          </button>
        </div>
      </form>
    </div>
  );
}
