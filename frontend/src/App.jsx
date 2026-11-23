import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { PublicLayout } from "./layouts/PublicLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";

import HomePage from "./pages/HomePage";
import { PrivacyPage, TermsPage } from "./pages/LegalPages";
import NotFoundPage from "./pages/NotFoundPage";
import { LoadingState } from "./components/Feedback";
import { RouteMetadata } from "./hooks/useDocumentTitle";
import { isDemoMode } from "./services/api";

const FacebookActivityPage = lazy(() => import("./pages/FacebookActivityPage"));
const FindCarePage = lazy(() => import("./pages/FindCarePage"));
const FacilityDetailPage = lazy(() => import("./pages/FacilityDetailPage"));
const SpecialistsPage = lazy(() => import("./pages/SpecialistsPage"));
const PractitionerDetailPage = lazy(
  () => import("./pages/PractitionerDetailPage"),
);
const LaboratoriesPage = lazy(() => import("./pages/LaboratoriesPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const GooglePlacesPage = lazy(() => import("./pages/GooglePlacesPage"));
const ProgramsPage = lazy(() => import("./pages/ProgramsPage"));
const ProgramDetailPage = lazy(() => import("./pages/ProgramDetailPage"));
const LibraryPage = lazy(() => import("./pages/LibraryPage"));
const HealthAlertsPage = lazy(() => import("./pages/HealthAlertsPage"));
const CarePlannerPage = lazy(() => import("./pages/CarePlannerPage"));
const ArticlePage = lazy(() => import("./pages/ArticlePage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));
const ExperiencesPage = lazy(() => import("./pages/ExperiencesPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const HowItWorksPage = lazy(() => import("./pages/HowItWorksPage"));
const TrustPage = lazy(() => import("./pages/TrustPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const SignInPage = lazy(() => import("./pages/SignInPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const VisitPreparationPage = lazy(() => import("./pages/VisitPreparationPage"));
const GoogleCallbackPage = lazy(() => import("./pages/GoogleCallbackPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const DashboardLayout = lazy(() =>
  import("./layouts/DashboardLayout").then((module) => ({
    default: module.DashboardLayout,
  })),
);

const PatientOverview = lazy(() => import("./pages/dashboard/PatientOverview"));
const MyAppointments = lazy(() => import("./pages/dashboard/MyAppointments"));
const SavedFacilities = lazy(() => import("./pages/dashboard/SavedFacilities"));
const MyRegistrations = lazy(() => import("./pages/dashboard/MyRegistrations"));
const MyReviews = lazy(() => import("./pages/dashboard/MyReviews"));
const Notifications = lazy(() => import("./pages/dashboard/Notifications"));
const AccountSettings = lazy(() => import("./pages/dashboard/AccountSettings"));
const FacilityOverview = lazy(
  () => import("./pages/dashboard/FacilityOverview"),
);
const FacilityAppointments = lazy(
  () => import("./pages/dashboard/FacilityAppointments"),
);
const FacilityProfile = lazy(() => import("./pages/dashboard/FacilityProfile"));
const FacilityReviews = lazy(() => import("./pages/dashboard/FacilityReviews"));
const AdminOverview = lazy(() => import("./pages/dashboard/AdminOverview"));
const AdminReviews = lazy(() => import("./pages/dashboard/AdminReviews"));
const AdminPrograms = lazy(() => import("./pages/dashboard/AdminPrograms"));
const AdminMessages = lazy(() => import("./pages/dashboard/AdminMessages"));
const AdminUsers = lazy(() => import("./pages/dashboard/AdminUsers"));
const AdminImports = lazy(() => import("./pages/dashboard/AdminImports"));
const AdminFacebookFeedback = lazy(
  () => import("./pages/dashboard/AdminFacebookFeedback"),
);

// Dashboard pages load on demand, so visitors who never sign in download less.
/** Every route in the app. Roles for each area are documented in docs/ROUTES_AND_ROLES.md. */
export default function App() {
  return (
    <Suspense
      fallback={
        <div className="container" style={{ padding: "48px 0" }}>
          <LoadingState rows={2} />
        </div>
      }
    >
      <RouteMetadata />
      {isDemoMode && (
        <div className="container" role="note">
          <p className="small callout callout-neutral">
            This copy uses sample listings and dates. Confirm current
            information directly with a facility.
          </p>
        </div>
      )}
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route
            path="find-care"
            element={<Navigate to="/find-care/facilities" replace />}
          />
          <Route
            path="find-care/facilities"
            element={<FindCarePage variant="facilities" />}
          />
          <Route
            path="find-care/insurance"
            element={<FindCarePage variant="insurance" />}
          />
          <Route
            path="find-care/map"
            element={<FindCarePage variant="map" />}
          />
          <Route path="find-care/specialists" element={<SpecialistsPage />} />
          <Route
            path="find-care/specialists/:slug"
            element={<PractitionerDetailPage />}
          />
          <Route path="find-care/laboratories" element={<LaboratoriesPage />} />
          <Route path="find-care/google" element={<GooglePlacesPage />} />
          <Route path="facebook-activity" element={<FacebookActivityPage />} />
          <Route path="facilities/:slug" element={<FacilityDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route
            path="health-community/free-care"
            element={<ProgramsPage variant="free" />}
          />
          <Route
            path="health-community/programmes"
            element={<ProgramsPage variant="all" />}
          />
          <Route path="programmes/:slug" element={<ProgramDetailPage />} />
          <Route
            path="health-community/alerts"
            element={<HealthAlertsPage />}
          />
          <Route path="care-planner" element={<CarePlannerPage />} />
          <Route path="health-library" element={<LibraryPage />} />
          <Route path="health-library/:slug" element={<ArticlePage />} />
          <Route
            path="prepare-for-your-visit"
            element={<VisitPreparationPage />}
          />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="patient-experiences" element={<ExperiencesPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="how-it-works" element={<HowItWorksPage />} />
          <Route path="trust" element={<TrustPage />} />
          <Route path="contact" element={<ContactPage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="terms" element={<TermsPage />} />
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
              <Route path="saved" element={<SavedFacilities />} />
              <Route path="registrations" element={<MyRegistrations />} />
              <Route path="reviews" element={<MyReviews />} />
            </Route>
            <Route
              path="facility"
              element={<ProtectedRoute roles={["facility_staff"]} />}
            >
              <Route index element={<FacilityOverview />} />
              <Route path="appointments" element={<FacilityAppointments />} />
              <Route path="profile" element={<FacilityProfile />} />
              <Route path="reviews" element={<FacilityReviews />} />
            </Route>
            <Route path="admin" element={<ProtectedRoute roles={["admin"]} />}>
              <Route index element={<AdminOverview />} />
              <Route path="reviews" element={<AdminReviews />} />
              <Route path="programmes" element={<AdminPrograms />} />
              <Route path="messages" element={<AdminMessages />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="imports" element={<AdminImports />} />
              <Route
                path="facebook-feedback"
                element={<AdminFacebookFeedback />}
              />
            </Route>
            <Route path="*" element={<NotFoundPage what="dashboard page" />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
