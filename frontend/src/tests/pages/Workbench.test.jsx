import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Workbench from '../../pages/Workbench'
import { useAlerts, useUpdateAlertStatus } from '../../hooks/useAlerts'
import { useFeedbackMutation } from '../../api/feedback'

vi.mock('../../hooks/useAlerts')
vi.mock('../../api/feedback', () => ({
  useFeedbackMutation: vi.fn()
}))

const renderWithRouter = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

describe('Workbench Component', () => {
  const mockAlerts = [
    { _id: '1', entity_key: 'host1:user1', threat_score: 0.9, log_type: 'network', threat_level: 'critical', timestamp: '2026-06-22T10:00:00Z' },
    { _id: '2', entity_key: 'host2:user2', threat_score: 0.6, log_type: 'process', threat_level: 'high', timestamp: '2026-06-22T10:05:00Z' }
  ]

  const mockUpdateStatus = vi.fn()
  const mockFeedback = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    useAlerts.mockReturnValue({
      data: { alerts: mockAlerts },
      isLoading: false
    })
    useUpdateAlertStatus.mockReturnValue({
      mutate: mockUpdateStatus
    })
    useFeedbackMutation.mockReturnValue({
      mutate: mockFeedback
    })
  })

  it('keyboard shortcut T submits true positive', () => {
    renderWithRouter(<Workbench />)
    
    expect(screen.getAllByText('host1:user1').length).toBeGreaterThan(0) // Initial selected

    fireEvent.keyDown(window, { key: 't', code: 'KeyT' })
    
    expect(mockFeedback).toHaveBeenCalledWith({
      alertId: '1',
      isMalicious: true,
      analystNotes: expect.stringContaining('Triaged via Workbench')
    })
    expect(mockUpdateStatus).toHaveBeenCalledWith({ id: '1', status: 'closed' })
  })

  it('keyboard shortcut N advances to next alert', () => {
    renderWithRouter(<Workbench />)
    
    // initially selected first
    expect(screen.getAllByText('host1:user1').length).toBeGreaterThan(0) // In queue + detail
    
    // press N
    fireEvent.keyDown(window, { key: 'n', code: 'KeyN' })
    
    // Detail view should now show second
    expect(screen.getAllByText('host2:user2').length).toBeGreaterThan(1) // Usually queue + header
  })

  it('shortcuts disabled when input field focused', () => {
    renderWithRouter(<Workbench />)
    
    // Add a dummy input to the body for testing
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    
    fireEvent.keyDown(input, { key: 't', code: 'KeyT' }) // firing on input simulating focus
    
    expect(mockFeedback).not.toHaveBeenCalled()
    expect(mockUpdateStatus).not.toHaveBeenCalled()
    
    document.body.removeChild(input)
  })
})
