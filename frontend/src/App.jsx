import { Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { PublicLayout } from './layouts/PublicLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import NotFoundPage from './pages/NotFoundPage';
import { LoadingState } from './components/Feedback';
import { DashboardHeader } from './components/DashboardParts';

// Feature pages are lazy-loaded and registered here by their workstreams, for example:
//   const FindCarePage = lazy(() => import('./pages/FindCarePage'));
//   <Route path="find-care/facilities" element={<FindCarePage />} />
// Navigation links to features that are not registered yet show the not-found page.

function DashboardHome() {
  return <DashboardHeader title="Dashboard" description="Patient, facility and administrator pages are added here by their workstreams." />;
}

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
            <Route index element={<DashboardHome />} />
            <Route path="*" element={<NotFoundPage what="dashboard page" />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
