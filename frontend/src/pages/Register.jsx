import { useState } from "react";
import { Link } from "react-router-dom";
import { client, setTokens } from "../api/client";

export default function Register() {
  const [form, setForm] = useState({
    username: "", password: "", confirmPassword: "",
    first_name: "", last_name: "", email: "", phone_number: "",
    applicant_type: "NGO",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    try {
      // eslint-disable-next-line no-unused-vars
      const { confirmPassword, ...payload } = form;
      const { data } = await client.post("/onboarding/register/", payload);
      setTokens(data);
      // Full reload (not client-side navigate) so AuthProvider re-mounts
      // and picks up the freshly-issued token from scratch.
      window.location.href = "/ngo-portal";
    } catch (err) {
      const detail = err.response?.data;
      setError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Could not register.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mono text-xs tracking-wide text-[var(--ink-soft)]">PS 26095</div>
          <h1 className="text-xl font-semibold text-[var(--ink)] mt-1">
            Register as NGO / Institute
          </h1>
          <p className="text-sm text-[var(--ink-soft)] mt-1">
            Create your login, then apply for a government scheme.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-[var(--line)] p-6 space-y-4">
          <label className="block text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">I am registering as</span>
            <select
              className="w-full border border-[var(--line)] px-3 py-2 bg-white"
              value={form.applicant_type}
              onChange={(e) => setForm({ ...form, applicant_type: e.target.value })}
            >
              <option value="NGO">NGO</option>
              <option value="INSTITUTE">Institute</option>
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Admin first name</span>
              <input className="w-full border border-[var(--line)] px-3 py-2"
                value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Admin last name</span>
              <input className="w-full border border-[var(--line)] px-3 py-2"
                value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </label>
          </div>

          <label className="block text-sm space-y-1">
            <span className="text-[var(--ink-soft)]">Username</span>
            <input required autoComplete="username" className="w-full border border-[var(--line)] px-3 py-2"
              value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Email</span>
              <input type="email" className="w-full border border-[var(--line)] px-3 py-2"
                value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Phone</span>
              <input className="w-full border border-[var(--line)] px-3 py-2"
                value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Password</span>
              <input required type="password" minLength={8} autoComplete="new-password"
                className="w-full border border-[var(--line)] px-3 py-2"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-[var(--ink-soft)]">Confirm password</span>
              <input required type="password" minLength={8} autoComplete="new-password"
                className="w-full border border-[var(--line)] px-3 py-2"
                value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} />
            </label>
          </div>

          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-[var(--ink)] text-white py-2 text-sm font-medium hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
          >
            {submitting ? "Creating account…" : "Register"}
          </button>
        </form>

        <p className="text-xs text-[var(--ink-soft)] text-center mt-4">
          Already have an account? <Link to="/login" className="text-[var(--accent)] underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
