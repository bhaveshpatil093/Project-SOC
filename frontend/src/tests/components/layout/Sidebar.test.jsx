import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Sidebar } from '../../../components/layout/Sidebar'
import { MemoryRouter } from 'react-router-dom'

// Mock stores & hooks
vi.mock('../../../store/uiStore', () => ({
  useUiStore: () => ({
    sidebarOpen: true,
    toggleSidebar: vi.fn(),
  }),
}))

vi.mock('../../../hooks/useMediaQuery', () => ({
  useIsTablet: () => false,
  useIsMobile: () => false,
}))

vi.mock('../../../contexts/AuthContext', () => ({
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
