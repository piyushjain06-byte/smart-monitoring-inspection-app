import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute, { OfficialRoute, FieldOfficerRoute, NGOPortalRoute } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import InspectorLayout from "./components/InspectorLayout";
import NGOPortalLayout from "./components/NGOPortalLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Institutes from "./pages/Institutes";
import InstituteDetail from "./pages/InstituteDetail";
import InspectorAssignments from "./pages/InspectorAssignments";
import SubmitInspection from "./pages/SubmitInspection";
import RoleRedirect from "./pages/RoleRedirect";
import Attendance from "./pages/Attendance";
import NGODashboard from "./pages/ngo/NGODashboard";
import NGOInstituteDetail from "./pages/ngo/NGOInstituteDetail";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* Government dashboard — District/State/Super Admin only */}
          <Route
            element={
              <OfficialRoute>
                <Layout />
              </OfficialRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/institutes" element={<Institutes />} />
            <Route path="/institutes/:id" element={<InstituteDetail />} />
            <Route path="/attendance" element={<Attendance />} />
          </Route>

          {/* Field inspector portal — Inspection Officer / PMU Team only */}
          <Route
            element={
              <FieldOfficerRoute>
                <InspectorLayout />
              </FieldOfficerRoute>
            }
          >
            <Route path="/inspector" element={<InspectorAssignments />} />
            <Route path="/inspector/assignments/:id/submit" element={<SubmitInspection />} />
          </Route>

          {/* NGO / Institute Admin & Project Incharge portal */}
          <Route
            element={
              <NGOPortalRoute>
                <NGOPortalLayout />
              </NGOPortalRoute>
            }
          >
            <Route path="/ngo-portal" element={<NGODashboard />} />
            <Route path="/ngo-portal/institutes/:id" element={<NGOInstituteDetail />} />
          </Route>

          {/* Fallback for any other authenticated path — routes by role */}
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <RoleRedirect />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
