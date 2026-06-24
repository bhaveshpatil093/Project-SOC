import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { NotificationDropdown } from '../../../components/layout/NotificationDropdown'

vi.mock('../../../store/notificationStore', () => ({
  useNotificationStore: () => ({
    settings: { browserEnabled: false, soundEnabled: false },
    history: [{ id: '1', title: 'Notif 1', body: 'Msg 1', level: 'critical' }],
    unreadCount: 1,
    markAllRead: vi.fn(),
  }),
}))

vi.mock('../../../hooks/useNotifications', () => ({
  useNotifications: () => ({
    requestPermission: vi.fn(),
    notificationPermission: 'default',
    playAlertSound: vi.fn(),
  }),
}))

describe('NotificationDropdown', () => {
  it('renders notification bell with unread indicator', () => {
    const { container } = render(<NotificationDropdown />)
    expect(container.querySelector('.animate-ping')).toBeInTheDocument()
  })
})
