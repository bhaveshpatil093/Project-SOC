import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { EntityTimeline } from '../../components/common/EntityTimeline'

// Mock formatters so we don't worry about dynamic dates
vi.mock('../../utils/formatters', () => ({
  formatRelativeTime: vi.fn(() => '2 mins ago'),
  formatTimestamp: vi.fn(() => '2026-06-22T00:00:00Z'),
  truncate: vi.fn((str) => str)
}))

const renderWithRouter = (ui) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('EntityTimeline Component', () => {
  const baseAlerts = [
    { id: '1', timestamp: '2026-06-22T10:00:00Z', threat_level: 'critical', top_rule: 'Rule A', threat_score: 0.9 },
    { id: '2', timestamp: '2026-06-22T10:05:00Z', threat_level: 'high', top_rule: 'Rule B', threat_score: 0.7 },
  ]

  it('renders timeline items for each alert', () => {
    renderWithRouter(<EntityTimeline alerts={baseAlerts} />)
    expect(screen.getByText('Rule A')).toBeInTheDocument()
    expect(screen.getByText('Rule B')).toBeInTheDocument()
  })

  it('highlights current alert with larger dot', () => {
    const { container } = renderWithRouter(<EntityTimeline alerts={baseAlerts} currentAlertId="1" />)
    // The current alert dot should have ring-2 and ring-blue-500
    const currentAlertContainer = container.querySelector('.ring-blue-500')
    expect(currentAlertContainer).toBeInTheDocument()
  })

  it('shows attack chain warning for 3+ events in 15 min', () => {
    const chainAlerts = [
      { id: '1', timestamp: '2026-06-22T10:00:00Z' },
      { id: '2', timestamp: '2026-06-22T10:05:00Z' },
      { id: '3', timestamp: '2026-06-22T10:10:00Z' },
    ]
    renderWithRouter(<EntityTimeline alerts={chainAlerts} />)
    expect(screen.getByText(/POTENTIAL ATTACK CHAIN DETECTED/i)).toBeInTheDocument()
  })

  it('compact mode renders condensed view', () => {
    renderWithRouter(<EntityTimeline alerts={baseAlerts} compact={true} />)
    // In compact mode, there shouldn't be the "View Alert" button, just the ArrowRight icon Link
    expect(screen.queryByText('View Alert')).not.toBeInTheDocument()
    // but the rules should still be visible
    expect(screen.getByText('Rule A')).toBeInTheDocument()
  })

  it('empty alerts array shows empty state', () => {
    renderWithRouter(<EntityTimeline alerts={[]} />)
    expect(screen.getByText(/No correlated events found for this entity/i)).toBeInTheDocument()
  })
})
