import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { isOfficial, isNGOPortalUser } from "../constants/roles";

export default function RoleRedirect() {
  const { user } = useAuth();
  if (isOfficial(user)) return <Navigate to="/" replace />;
  if (isNGOPortalUser(user)) return <Navigate to="/ngo-portal" replace />;
  return <Navigate to="/inspector" replace />;
}
