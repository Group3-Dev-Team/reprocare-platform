import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, HashRouter } from 'react-router-dom';
import '@fontsource-variable/plus-jakarta-sans';
import './styles/tokens.css';
import './styles/base.css';
import './styles/components.css';
import './styles/layout.css';
import './styles/pages.css';
import './styles/dashboard.css';
import './styles/refinements.css';
import './styles/polish.css';
import './styles/experience.css';
import './styles/brand.css';
import './styles/theme.css';
import App from './App';
import { isDemoMode } from './services/api';
import { AuthProvider } from './hooks/useAuth';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { initializeTheme } from './hooks/useTheme';

initializeTheme();

// The single-file preview build uses hash URLs because it has no server to rewrite paths.
const Router = isDemoMode ? HashRouter : BrowserRouter;

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ToastProvider>
          <ErrorBoundary>
            <App />
          </ErrorBoundary>
        </ToastProvider>
      </AuthProvider>
    </Router>
  </React.StrictMode>,
);
