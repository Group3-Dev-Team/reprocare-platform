import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { PublicLayout } from "./layouts/PublicLayout";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";
import { PrivacyPage, TermsPage } from "./pages/LegalPages";
import { LoadingState } from "./components/Feedback";
import { RouteMetadata } from "./hooks/useDocumentTitle";

// Facility discovery, maps and specialists (SCRUM-14)
const FindCarePage = lazy(() => import("./pages/FindCarePage"));
const FacilityDetailPage = lazy(() => import("./pages/FacilityDetailPage"));
const SpecialistsPage = lazy(() => import("./pages/SpecialistsPage"));
const PractitionerDetailPage = lazy(() => import("./pages/PractitionerDetailPage"));
const LaboratoriesPage = lazy(() => import("./pages/LaboratoriesPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const GooglePlacesPage = lazy(() => import("./pages/GooglePlacesPage"));
const LivePlacePage = lazy(() => import("./pages/LivePlacePage"));
const FacebookActivityPage = lazy(() => import("./pages/FacebookActivityPage"));
const ExperiencesPage = lazy(() => import("./pages/ExperiencesPage"));
const SavedFacilities = lazy(() => import("./pages/dashboard/SavedFacilities"));

// Programmes, health content and public pages (SCRUM-16)
const ProgramsPage = lazy(() => import("./pages/ProgramsPage"));
const ProgramDetailPage = lazy(() => import("./pages/ProgramDetailPage"));
const LibraryPage = lazy(() => import("./pages/LibraryPage"));
const ArticlePage = lazy(() => import("./pages/ArticlePage"));
const HealthAlertsPage = lazy(() => import("./pages/HealthAlertsPage"));
const CarePlannerPage = lazy(() => import("./pages/CarePlannerPage"));
const VisitPreparationPage = lazy(() => import("./pages/VisitPreparationPage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const HowItWorksPage = lazy(() => import("./pages/HowItWorksPage"));
const TrustPage = lazy(() => import("./pages/TrustPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const AdminPrograms = lazy(() => import("./pages/dashboard/AdminPrograms"));
const AdminArticles = lazy(() => import("./pages/dashboard/AdminArticles"));
const AdminImports = lazy(() => import("./pages/dashboard/AdminImports"));

// Appointments, reviews and dashboards (SCRUM-15)
const PatientOverview = lazy(() => import("./pages/dashboard/PatientOverview"));
const MyAppointments = lazy(() => import("./pages/dashboard/MyAppointments"));
const MyRegistrations = lazy(() => import("./pages/dashboard/MyRegistration"));
const MyReviews = lazy(() => import("./pages/dashboard/MyReviews"));
const Notifications = lazy(() => import("./pages/dashboard/Notifications"));
const FacilityOverview = lazy(
  () => import("./pages/dashboard/FacilityOverview"),
);
const FacilityAppointments = lazy(
  () => import("./pages/dashboard/FacilityAppointments"),
);
const FacilityReviews = lazy(() => import("./pages/dashboard/FacilityReviews"));
const FacilityProfile = lazy(() => import("./pages/dashboard/FacilityProfile"));
const AdminReviews = lazy(() => import("./pages/dashboard/AdminReviews"));
const AdminFacebookFeedback = lazy(
  () => import("./pages/dashboard/AdminFacebookFeedback"),
);

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
      <RouteMetadata />
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="find-care" element={<Navigate to="/find-care/facilities" replace />} />
          <Route path="find-care/facilities" element={<FindCarePage variant="facilities" />} />
          <Route path="find-care/insurance" element={<FindCarePage variant="insurance" />} />
          <Route path="find-care/map" element={<FindCarePage variant="map" />} />
          <Route path="find-care/specialists" element={<SpecialistsPage />} />
          <Route path="find-care/specialists/:slug" element={<PractitionerDetailPage />} />
          <Route path="find-care/laboratories" element={<LaboratoriesPage />} />
          <Route path="find-care/google" element={<GooglePlacesPage />} />
          <Route path="find-care/google/place/:placeId" element={<LivePlacePage />} />
          <Route path="facebook-activity" element={<FacebookActivityPage />} />
          <Route path="facilities/:slug" element={<FacilityDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="health-community/free-care" element={<ProgramsPage variant="free" />} />
          <Route path="health-community/programmes" element={<ProgramsPage variant="all" />} />
          <Route path="programmes/:slug" element={<ProgramDetailPage />} />
          <Route path="health-community/alerts" element={<HealthAlertsPage />} />
          <Route path="care-planner" element={<CarePlannerPage />} />
          <Route path="health-library" element={<LibraryPage />} />
          <Route path="health-library/:slug" element={<ArticlePage />} />
          <Route path="prepare-for-your-visit" element={<VisitPreparationPage />} />
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
              <Route path="reviews" element={<FacilityReviews />} />
              <Route path="profile" element={<FacilityProfile />} />
            </Route>
            <Route path="admin" element={<ProtectedRoute roles={["admin"]} />}>
              <Route index element={<AdminOverview />} />
              <Route path="reviews" element={<AdminReviews />} />
              <Route path="programmes" element={<AdminPrograms />} />
              <Route path="articles" element={<AdminArticles />} />
              <Route path="imports" element={<AdminImports />} />
              <Route
                path="facebook-feedback"
                element={<AdminFacebookFeedback />}
              />
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
