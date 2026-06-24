import os

tests = {
    "TopBar.test.jsx": """import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TopBar } from '../../components/layout/TopBar'
import { MemoryRouter } from 'react-router-dom'

// Mock dependencies
vi.mock('../../store/uiStore', () => ({
  useUiStore: () => ({
    toggleSidebar: vi.fn(),
  }),
}))

vi.mock('../../store/preferencesStore', () => ({
  usePreferencesStore: () => ({
    theme: 'dark',
    setPreference: vi.fn(),
  }),
}))

vi.mock('../../components/layout/NotificationDropdown', () => ({
  NotificationDropdown: () => <div data-testid="mock-notif-dropdown">NotifDropdown</div>,
}))

vi.mock('../../components/layout/PlatformHealthDropdown', () => ({
  PlatformHealthDropdown: () => <div data-testid="mock-health-dropdown">HealthDropdown</div>,
}))

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: [{ start_time: '2026-01-01T00:00:00Z' }],
  }),
}))

const renderTopBar = (initialRoute = '/dashboard') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <TopBar />
    </MemoryRouter>
  )
}

describe('TopBar', () => {
  it('renders correctly', () => {
    renderTopBar()
    expect(screen.getByText('Dashboard Analytics')).toBeInTheDocument()
    expect(screen.getByTestId('mock-notif-dropdown')).toBeInTheDocument()
    expect(screen.getByTestId('mock-health-dropdown')).toBeInTheDocument()
  })

  it('updates title based on route', () => {
    renderTopBar('/alerts')
    expect(screen.getByText('Security Alerts')).toBeInTheDocument()
  })
})
""",
    "Sidebar.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Sidebar } from '../../components/layout/Sidebar'
import { MemoryRouter } from 'react-router-dom'

// Mock stores & hooks
vi.mock('../../store/uiStore', () => ({
  useUiStore: () => ({
    sidebarOpen: true,
    toggleSidebar: vi.fn(),
  }),
}))

vi.mock('../../hooks/useMediaQuery', () => ({
  useIsTablet: () => false,
  useIsMobile: () => false,
}))

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { role: 'admin' },
  }),
}))

const renderSidebar = () => {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('renders navigation items', () => {
    renderSidebar()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Alerts')).toBeInTheDocument()
    expect(screen.getByText('ISRO SOC')).toBeInTheDocument()
  })

  it('renders System Monitor for admin', () => {
    renderSidebar()
    expect(screen.getByText('System Monitor')).toBeInTheDocument()
  })
})
""",
    "AlertNotificationBanner.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AlertNotificationBanner } from '../../components/layout/AlertNotificationBanner'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../../store/bannerStore', () => ({
  useBannerStore: () => ({
    banners: [{ id: '1', type: 'critical', message: 'Test critical alert', actionPath: '/alerts' }],
    removeBanner: vi.fn(),
  }),
}))

describe('AlertNotificationBanner', () => {
  it('renders active banners', () => {
    render(
      <MemoryRouter>
        <AlertNotificationBanner />
      </MemoryRouter>
    )
    expect(screen.getByText('Test critical alert')).toBeInTheDocument()
    expect(screen.getByRole('link')).toHaveAttribute('href', '/alerts')
  })
})
""",
    "NotificationDropdown.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { NotificationDropdown } from '../../components/layout/NotificationDropdown'

vi.mock('../../hooks/useNotifications', () => ({
  useNotifications: () => ({
    notifications: [{ id: '1', title: 'Notif 1', message: 'Msg 1', is_read: false }],
    unreadCount: 1,
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    deleteNotification: vi.fn(),
  }),
}))

describe('NotificationDropdown', () => {
  it('renders notification bell with unread count', () => {
    render(<NotificationDropdown />)
    expect(screen.getByText('1')).toBeInTheDocument() // unread badge
  })
})
""",
    "PlatformHealthDropdown.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PlatformHealthDropdown } from '../../components/layout/PlatformHealthDropdown'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: { status: 'healthy', version: '1.0.0' },
    isLoading: false,
    isError: false,
  }),
}))

describe('PlatformHealthDropdown', () => {
  it('renders health status', () => {
    render(<PlatformHealthDropdown />)
    expect(screen.getByText('healthy')).toBeInTheDocument()
  })
})
""",
    "ProtectedRoute.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProtectedRoute } from '../../components/layout/ProtectedRoute'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthContext } from '../../contexts/AuthContext'

describe('ProtectedRoute', () => {
  const renderWithAuth = (user, requiredRole) => {
    return render(
      <AuthContext.Provider value={{ user, loading: false }}>
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route path="/unauthorized" element={<div>Unauthorized Page</div>} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute requiredRole={requiredRole}>
                  <div>Protected Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    )
  }

  it('redirects to login if not authenticated', () => {
    renderWithAuth(null)
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('redirects to unauthorized if role does not match', () => {
    renderWithAuth({ role: 'viewer' }, 'admin')
    expect(screen.getByText('Unauthorized Page')).toBeInTheDocument()
  })

  it('renders content if authenticated and role matches', () => {
    renderWithAuth({ role: 'admin' }, 'admin')
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })
})
"""
}

os.makedirs('src/tests/components/layout', exist_ok=True)
for filename, content in tests.items():
    with open(f"src/tests/components/layout/{filename}", "w") as f:
        f.write(content)
