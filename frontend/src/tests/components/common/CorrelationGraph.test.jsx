import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CorrelationGraph } from '../../../components/common/CorrelationGraph'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: { nodes: [], links: [] }, isLoading: false }),
}))

// Mock ResizeObserver
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('CorrelationGraph', () => {
  it('renders graph component', () => {
    const { container } = render(
      <MemoryRouter>
        <CorrelationGraph alertId="1" />
      </MemoryRouter>
    )
    expect(container).toBeInTheDocument()
  })
})
