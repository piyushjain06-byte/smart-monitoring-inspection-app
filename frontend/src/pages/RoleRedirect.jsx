import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { isOfficial } from "../constants/roles";

export default function RoleRedirect() {
  const { user } = useAuth();
  return <Navigate to={isOfficial(user) ? "/" : "/inspector"} replace />;
}
