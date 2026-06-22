import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { CorrelationGraph } from '../../components/common/CorrelationGraph'

// Mock preferences store
vi.mock('../../store/preferencesStore', () => ({
  usePreferencesStore: () => ({ theme: 'dark' })
}))
vi.mock('../../store/uiStore', () => ({
  useUiStore: () => ({})
}))

// We need to mock D3 fully to avoid errors in JSDOM environment
vi.mock('d3', () => {
  const d3Mock = {
    select: vi.fn().mockReturnValue({
      selectAll: vi.fn().mockReturnThis(),
      remove: vi.fn().mockReturnThis(),
      append: vi.fn().mockReturnThis(),
      attr: vi.fn().mockReturnThis(),
      style: vi.fn().mockReturnThis(),
      call: vi.fn().mockReturnThis(),
      data: vi.fn().mockReturnThis(),
      join: vi.fn().mockReturnThis(),
      each: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
      text: vi.fn().mockReturnThis()
    }),
    zoomIdentity: { x: 0, y: 0, k: 1 },
    zoom: vi.fn().mockReturnValue({
      scaleExtent: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis()
    }),
    forceSimulation: vi.fn().mockReturnValue({
      force: vi.fn().mockReturnThis(),
      alphaDecay: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
      stop: vi.fn()
    }),
    forceLink: vi.fn().mockReturnValue({
      id: vi.fn().mockReturnThis(),
      distance: vi.fn().mockReturnThis()
    }),
    forceManyBody: vi.fn().mockReturnValue({ strength: vi.fn().mockReturnThis() }),
    forceCenter: vi.fn(),
    forceCollide: vi.fn().mockReturnValue({ radius: vi.fn().mockReturnThis() }),
    drag: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnThis(),
      container: vi.fn().mockReturnThis(),
      subject: vi.fn().mockReturnThis()
    })
  }
  return d3Mock
})

describe('CorrelationGraph Component', () => {
  const incidents = [
    { incident_id: 'INC-1', entity_key: 'h1:u1', incident_threat_score: 0.9, host_id: 'h1', user_name: 'u1' }
  ]
  
  const alerts = [
    { id: 'ALT-1', threat_score: 0.8, host_id: 'h1' },
    { id: 'ALT-2', threat_score: 0.5, host_id: 'h2' }
  ]

  const renderWithRouter = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

  it('renders loading state initially then UI', async () => {
    // Note: React 18 / dynamic import of D3 means we start with loading
    renderWithRouter(<CorrelationGraph incidents={incidents} alerts={alerts} />)
    
    // Check loading state or directly wait for controls overlay
    await waitFor(() => {
      expect(screen.getByText(/Reset Layout/i)).toBeInTheDocument()
    })
  })

  it('renders nodes for incidents and alerts (indicated by text)', async () => {
    renderWithRouter(<CorrelationGraph incidents={incidents} alerts={alerts} />)
    
    await waitFor(() => {
      // 1 incident node, 1 host node (h1), 1 user node (u1)
      // 2 alert nodes, 1 host node (h2)
      // Total = 1(INC) + 1(h1) + 1(u1) + 2(ALT) + 1(h2) = 6 nodes
      expect(screen.getByText(/Showing 6 nodes/i)).toBeInTheDocument()
    })
  })

  it('respects maxNodes limit and clusters nodes when exceeded', async () => {
    // maxNodes = 2
    renderWithRouter(<CorrelationGraph incidents={incidents} alerts={alerts} maxNodes={2} />)
    
    await waitFor(() => {
      // It should drop to 2 nodes
      expect(screen.getByText(/Showing 2 nodes/i)).toBeInTheDocument()
    })
  })

  // We can't perfectly test onNodeClick through d3 mock events easily in standard RTL without complex d3 simulation injection,
  // but we can verify the handler prop is accepted. For a true event test, more complex d3 mocking is needed.
})
