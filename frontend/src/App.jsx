import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { PublicLayout } from "./layouts/PublicLayout";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";
import { LoadingState } from "./components/Feedback";

// Appointments, reviews and dashboards (SCRUM-15). Other workstreams register their pages the same way.
const PatientOverview = lazy(() => import("./pages/dashboard/PatientOverview"));
const MyAppointments = lazy(() => import("./pages/dashboard/MyAppointments"));
const MyReviews = lazy(() => import("./pages/dashboard/MyReviews"));
const Notifications = lazy(() => import("./pages/dashboard/Notifications"));
const FacilityOverview = lazy(
  () => import("./pages/dashboard/FacilityOverview"),
);
const FacilityAppointments = lazy(
  () => import("./pages/dashboard/FacilityAppointments"),
);
const FacilityReviews = lazy(() => import("./pages/dashboard/FacilityReviews"));
const AdminReviews = lazy(() => import("./pages/dashboard/AdminReviews"));

// Sign in, accounts and administration (SCRUM-13)
const SignInPage = lazy(() => import("./pages/SignInPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const GoogleCallbackPage = lazy(() => import("./pages/GoogleCallbackPage"));
const AccountSettings = lazy(() => import("./pages/dashboard/AccountSettings"));
const AdminOverview = lazy(() => import("./pages/dashboard/AdminOverview"));
const AdminUsers = lazy(() => import("./pages/dashboard/AdminUsers"));
const AdminMessages = lazy(() => import("./pages/dashboard/AdminMessages"));

export default function App() {
  return (
    <Suspense fallback={<LoadingState rows={1} height={240} />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="sign-in" element={<SignInPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
          <Route path="reset-password" element={<ResetPasswordPage />} />
          <Route path="auth/google/callback" element={<GoogleCallbackPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="dashboard" element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            <Route path="notifications" element={<Notifications />} />
            <Route path="account" element={<AccountSettings />} />
            <Route element={<ProtectedRoute roles={["patient"]} />}>
              <Route index element={<PatientOverview />} />
              <Route path="appointments" element={<MyAppointments />} />
              <Route path="reviews" element={<MyReviews />} />
            </Route>
            <Route
              path="facility"
              element={<ProtectedRoute roles={["facility_staff"]} />}
            >
              <Route index element={<FacilityOverview />} />
              <Route path="appointments" element={<FacilityAppointments />} />
              <Route path="reviews" element={<FacilityReviews />} />
            </Route>
            <Route path="admin" element={<ProtectedRoute roles={["admin"]} />}>
              <Route index element={<AdminOverview />} />
              <Route path="reviews" element={<AdminReviews />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="messages" element={<AdminMessages />} />
            </Route>
            <Route path="*" element={<NotFoundPage what="dashboard page" />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
