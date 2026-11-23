import { lazy, Suspense } from "react";


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
              <Route path="profile" element={<FacilityProfile />} />
            </Route>
            <Route path="admin" element={<ProtectedRoute roles={["admin"]} />}>
              <Route index element={<AdminOverview />} />
              <Route path="reviews" element={<AdminReviews />} />

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
