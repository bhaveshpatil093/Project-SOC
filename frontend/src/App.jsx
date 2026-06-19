import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { AlertNotificationBanner } from './components/layout/AlertNotificationBanner';
import { Dashboard } from './pages/Dashboard';
import { Alerts } from './pages/Alerts';
import { AlertDetail } from './pages/AlertDetail';
import { Investigation } from './pages/Investigation';
import { Feedback } from './pages/Feedback';
import { Settings } from './pages/Settings';
import { Training } from './pages/Training';
import { Login } from './pages/Login';
import { useWebSocket } from './hooks/useWebSocket';
import { AlertTriangle } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';

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
      <Routes>
        <Route path="/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
            <Route path="alerts" element={<ErrorBoundary><Alerts /></ErrorBoundary>} />
            <Route path="alerts/:id" element={<ErrorBoundary><AlertDetail /></ErrorBoundary>} />
            <Route path="investigation" element={<ErrorBoundary><Investigation /></ErrorBoundary>} />
            <Route path="feedback" element={<ErrorBoundary><Feedback /></ErrorBoundary>} />
            <Route path="training" element={<ErrorBoundary><Training /></ErrorBoundary>} />
            <Route path="settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
            <Route path="*" element={<ErrorBoundary><NotFound /></ErrorBoundary>} />
          </Route>
        </Route>
      </Routes>
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
