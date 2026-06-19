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
import { useWebSocket } from './hooks/useWebSocket';
import { AlertTriangle } from 'lucide-react';

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
  // Initialize WebSocket connection universally across the whole single page lifecycle.
  useWebSocket();
  
  return (
    <>
      <AlertNotificationBanner />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="alerts/:id" element={<AlertDetail />} />
          <Route path="investigation" element={<Investigation />} />
          <Route path="feedback" element={<Feedback />} />
          <Route path="training" element={<Training />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
};

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
