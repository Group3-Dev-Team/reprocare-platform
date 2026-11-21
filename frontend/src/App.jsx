import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { PublicLayout } from './layouts/PublicLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import NotFoundPage from './pages/NotFoundPage';
import { LoadingState } from './components/Feedback';

// Appointments, reviews and dashboards (SCRUM-15). Other workstreams register their pages the same way.
const PatientOverview = lazy(() => import('./pages/dashboard/PatientOverview'));
const MyAppointments = lazy(() => import('./pages/dashboard/MyAppointments'));
const Notifications = lazy(() => import('./pages/dashboard/Notifications'));
const FacilityOverview = lazy(() => import('./pages/dashboard/FacilityOverview'));
const FacilityAppointments = lazy(() => import('./pages/dashboard/FacilityAppointments'));

export default function App() {
  return (
    <Suspense fallback={<LoadingState rows={1} height={240} />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="dashboard" element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            <Route path="notifications" element={<Notifications />} />
            <Route element={<ProtectedRoute roles={['patient']} />}>
              <Route index element={<PatientOverview />} />
              <Route path="appointments" element={<MyAppointments />} />
            </Route>
            <Route path="facility" element={<ProtectedRoute roles={['facility_staff']} />}>
              <Route index element={<FacilityOverview />} />
              <Route path="appointments" element={<FacilityAppointments />} />
            </Route>
            <Route path="*" element={<NotFoundPage what="dashboard page" />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
