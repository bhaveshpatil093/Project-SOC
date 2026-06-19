import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { AlertNotificationBanner } from './components/layout/AlertNotificationBanner';
import { useWebSocket } from './hooks/useWebSocket';
import { AlertTriangle } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSpinner } from './components/common/LoadingSpinner';

const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Alerts = lazy(() => import('./pages/Alerts').then(m => ({ default: m.Alerts })));
const AlertDetail = lazy(() => import('./pages/AlertDetail').then(m => ({ default: m.AlertDetail })));
const Incidents = lazy(() => import('./pages/Incidents').then(m => ({ default: m.Incidents })));
const Investigation = lazy(() => import('./pages/Investigation').then(m => ({ default: m.Investigation })));
const Feedback = lazy(() => import('./pages/Feedback').then(m => ({ default: m.Feedback })));
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const Training = lazy(() => import('./pages/Training').then(m => ({ default: m.Training })));
const Login = lazy(() => import('./pages/Login').then(m => ({ default: m.Login })));


const NotFound = () => (
  <div className="flex flex-col items-center justify-center h-full min-h-[500px]">
    <div className="p-4 bg-slate-800 rounded-full mb-6 text-slate-500">
      <AlertTriangle className="h-12 w-12" />
    </div>
    <h2 className="text-3xl font-bold text-white mb-3">404 — Null Route Trajectory</h2>
    <p className="text-slate-400">The requested endpoint hash does not map to any active internal layout components.</p>
  </div>
);

const AppContent = () => {
  const { isAuthenticated } = useAuth();
  
  // Initialize WebSocket connection universally across the whole single page lifecycle ONLY when authenticated
  useWebSocket(isAuthenticated);
  
  return (
    <>
      <AlertNotificationBanner />
      <Suspense fallback={<div className="h-screen w-full flex items-center justify-center bg-slate-950"><LoadingSpinner /></div>}>
        <Routes>
          <Route path="/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
              <Route path="alerts" element={<ErrorBoundary><Alerts /></ErrorBoundary>} />
              <Route path="alerts/:id" element={<ErrorBoundary><AlertDetail /></ErrorBoundary>} />
              <Route path="incidents" element={<ErrorBoundary><Incidents /></ErrorBoundary>} />
              <Route path="investigation" element={<ErrorBoundary><Investigation /></ErrorBoundary>} />
              <Route path="feedback" element={<ErrorBoundary><Feedback /></ErrorBoundary>} />
              <Route path="training" element={<ErrorBoundary><Training /></ErrorBoundary>} />
              <Route path="settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
              <Route path="*" element={<ErrorBoundary><NotFound /></ErrorBoundary>} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
