import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AlertNotificationBanner } from '../../../components/layout/AlertNotificationBanner'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../../../store/bannerStore', () => ({
  useBannerStore: () => ({
    banners: [{ _ws_id: 'ws1', _id: '123', threat_level: 'critical', threat_score: 0.95, host_id: 'Test Host', log_type: 'syslog' }],
    removeBanner: vi.fn(),
  }),
}))

describe('AlertNotificationBanner', () => {
  it('renders active banners and navigates on view', () => {
    let locationPath = ''
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<AlertNotificationBanner />} />
          <Route path="/alerts/:id" element={<div>Alert Page</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('NEW critical ALERT')).toBeInTheDocument()
    expect(screen.getByText('Test Host')).toBeInTheDocument()
    
    fireEvent.click(screen.getByText('View Alert'))
    expect(screen.getByText('Alert Page')).toBeInTheDocument()
  })
})
