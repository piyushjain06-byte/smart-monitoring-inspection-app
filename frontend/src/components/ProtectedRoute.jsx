import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { isOfficial, isFieldOfficer } from "../constants/roles";

function LoadingScreen() {
  return (
    <div className="h-screen flex items-center justify-center text-[var(--ink-soft)]">
      Loading…
    </div>
  );
}

/** Any authenticated user. */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

/** District/State/Super Admin only — sends field officers to their own portal. */
export function OfficialRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (!isOfficial(user)) return <Navigate to="/inspector" replace />;
  return children;
}

/** Inspection Officer / PMU Team only — sends officials to the main dashboard. */
export function FieldOfficerRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (!isFieldOfficer(user)) return <Navigate to="/" replace />;
  return children;
}
