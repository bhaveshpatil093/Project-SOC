import React, { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { AlertNotificationBanner } from './components/layout/AlertNotificationBanner'
import { useWebSocket } from './hooks/useWebSocket'
import { AlertTriangle } from 'lucide-react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { LoadingSpinner } from './components/common/LoadingSpinner'
import { applyTheme } from './utils/theme'
import { usePreferencesStore } from './store/preferencesStore'
import { PageTransition } from './components/layout/PageTransition'
import { OnboardingWizard } from './components/onboarding/OnboardingWizard'

// Apply initial theme on app startup
applyTheme(usePreferencesStore.getState().theme)

const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))
const Alerts = lazy(() => import('./pages/Alerts').then((m) => ({ default: m.Alerts })))
const AlertDetail = lazy(() =>
  import('./pages/AlertDetail').then((m) => ({ default: m.AlertDetail })),
)
const Incidents = lazy(() => import('./pages/Incidents').then((m) => ({ default: m.Incidents })))
const Investigation = lazy(() =>
  import('./pages/Investigation').then((m) => ({ default: m.Investigation })),
)
const Feedback = lazy(() => import('./pages/Feedback').then((m) => ({ default: m.Feedback })))
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })))
const Hunting = lazy(() => import('./pages/Hunting').then(m => ({ default: m.Hunting })))
const Training = lazy(() => import('./pages/Training').then((m) => ({ default: m.Training })))
const Login = lazy(() => import('./pages/Login').then((m) => ({ default: m.Login })))
const SystemMonitor = lazy(() => import('./pages/SystemMonitor').then((m) => ({ default: m.SystemMonitor })))
const Diagnostics = lazy(() => import('./pages/Diagnostics').then((m) => ({ default: m.Diagnostics })))

const NotFound = () => (
  <div className="flex flex-col items-center justify-center h-full min-h-[500px]">
    <div className="p-4 bg-[var(--bg-secondary)] rounded-full mb-6 text-[var(--text-secondary)]">
      <AlertTriangle className="h-12 w-12" />
    </div>
    <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-3">
      404 — Null Route Trajectory
    </h2>
    <p className="text-[var(--text-secondary)]">
      The requested endpoint hash does not map to any active internal layout components.
    </p>
  </div>
)

const AppContent = () => {
  const { isAuthenticated } = useAuth()

  // Initialize WebSocket connection universally across the whole single page lifecycle ONLY when authenticated
  useWebSocket(isAuthenticated)

  return (
    <>
      <AlertNotificationBanner />
      {isAuthenticated && <OnboardingWizard />}
      <Suspense
        fallback={
          <div className="h-screen w-full flex items-center justify-center bg-[var(--bg-primary)]">
            <LoadingSpinner />
          </div>
        }
      >
        <Routes>
          <Route
            path="/login"
            element={
              <ErrorBoundary>
                <PageTransition><Login /></PageTransition>
              </ErrorBoundary>
            }
          />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route
                path="dashboard"
                element={
                  <ErrorBoundary>
                    <PageTransition><Dashboard /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="alerts"
                element={
                  <ErrorBoundary>
                    <PageTransition><Alerts /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="alerts/:id"
                element={
                  <ErrorBoundary>
                    <PageTransition><AlertDetail /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="incidents"
                element={
                  <ErrorBoundary>
                    <PageTransition><Incidents /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="investigation"
                element={
                  <ErrorBoundary>
                    <PageTransition><Investigation /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="feedback"
                element={
                  <ErrorBoundary>
                    <PageTransition><Feedback /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="training"
                element={
                  <ErrorBoundary>
                    <PageTransition><Training /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="settings"
                element={
                  <ErrorBoundary>
                    <PageTransition><Settings /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="system"
                element={
                  <ErrorBoundary>
                    <PageTransition><SystemMonitor /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="diagnostics"
                element={
                  <ErrorBoundary>
                    <PageTransition><Diagnostics /></PageTransition>
                  </ErrorBoundary>
                }
              />
              <Route
                path="*"
                element={
                  <ErrorBoundary>
                    <PageTransition><NotFound /></PageTransition>
                  </ErrorBoundary>
                }
              />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </>
  )
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Router>
          <AppContent />
        </Router>
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
