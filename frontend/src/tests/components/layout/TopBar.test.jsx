import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TopBar } from '../../../components/layout/TopBar'
import { MemoryRouter } from 'react-router-dom'

// Mock dependencies
vi.mock('../../../store/uiStore', () => ({
  useUiStore: () => ({
    toggleSidebar: vi.fn(),
  }),
}))

vi.mock('../../../store/preferencesStore', () => ({
  usePreferencesStore: () => ({
    theme: 'dark',
    setPreference: vi.fn(),
  }),
}))

vi.mock('../../../components/layout/NotificationDropdown', () => ({
  NotificationDropdown: () => <div data-testid="mock-notif-dropdown">NotifDropdown</div>,
}))

vi.mock('../../../components/layout/PlatformHealthDropdown', () => ({
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
