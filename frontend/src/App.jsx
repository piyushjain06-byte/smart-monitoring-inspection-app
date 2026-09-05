import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute, { OfficialRoute, FieldOfficerRoute, NGOPortalRoute } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import InspectorLayout from "./components/InspectorLayout";
import NGOPortalLayout from "./components/NGOPortalLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Institutes from "./pages/Institutes";
import InstituteDetail from "./pages/InstituteDetail";
import ReportDetail from "./pages/ReportDetail";
import InspectorAssignments from "./pages/InspectorAssignments";
import SubmitInspection from "./pages/SubmitInspection";
import RoleRedirect from "./pages/RoleRedirect";
import Attendance from "./pages/Attendance";
import Manage from "./pages/admin/Manage";
import InspectionTemplates from "./pages/admin/InspectionTemplates";
import TemplateDetail from "./pages/admin/TemplateDetail";
import SchemeApplications from "./pages/admin/SchemeApplications";
import NGODashboard from "./pages/ngo/NGODashboard";
import NGOInstituteDetail from "./pages/ngo/NGOInstituteDetail";
import ApplyForScheme from "./pages/ngo/ApplyForScheme";
import MyApplications from "./pages/ngo/MyApplications";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          {/* Public NGO/Institute self-registration (PS 26095 onboarding flow) */}
          <Route path="/register" element={<Register />} />

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
            <Route path="/institutes/:instituteId/reports/:assignmentId" element={<ReportDetail />} />
            <Route path="/attendance" element={<Attendance />} />
            <Route path="/templates" element={<InspectionTemplates />} />
            <Route path="/templates/:id" element={<TemplateDetail />} />
            <Route path="/manage" element={<Manage />} />
            {/* Government Review step — backend still enforces Super-Admin-only
                approve/reject even if a non-super-admin official opens this URL directly. */}
            <Route path="/scheme-applications" element={<SchemeApplications />} />
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
            <Route path="/inspector/reports/:assignmentId" element={<ReportDetail />} />
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
            {/* Onboarding flow: apply for a scheme / track application status.
                A freshly-registered account has zero institutes until one of
                these applications is approved — see NGODashboard's empty state. */}
            <Route path="/ngo-portal/apply" element={<ApplyForScheme />} />
            <Route path="/ngo-portal/applications" element={<MyApplications />} />
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
