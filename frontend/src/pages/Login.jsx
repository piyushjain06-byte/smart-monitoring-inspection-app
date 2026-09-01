import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { client } from "../api/client";
import { isOfficial } from "../constants/roles";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      // login() only sets tokens; fetch the profile once more here so we can
      // route immediately without waiting on AuthContext's next render.
      const { data: me } = await client.get("/accounts/me/");
      navigate(isOfficial(me) ? "/" : "/inspector", { replace: true });
    } catch {
      setError("Username or password is incorrect.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mono text-xs tracking-wide text-[var(--ink-soft)]">PS 26095</div>
          <h1 className="text-xl font-semibold text-[var(--ink)] mt-1">
            Smart Monitoring &amp; Inspection Platform
          </h1>
          <p className="text-sm text-[var(--ink-soft)] mt-1">Sign in to your account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white border border-[var(--line)] p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              className="w-full border border-[var(--line)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="w-full border border-[var(--line)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-[var(--ink)] text-white py-2 text-sm font-medium hover:bg-[var(--accent)] transition-colors disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-xs text-[var(--ink-soft)] text-center mt-4">
          Use your Django admin credentials — same login, one platform.
        </p>
      </div>
    </div>
  );
}
