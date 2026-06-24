import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { WebhooksPanel } from '../../../components/preferences/WebhooksPanel'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [], isLoading: false }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() })
}))

describe('WebhooksPanel', () => {
  it('renders webhooks header', () => {
    render(<WebhooksPanel />)
    expect(screen.getByText(/API Webhooks/i)).toBeInTheDocument()
  })
})
