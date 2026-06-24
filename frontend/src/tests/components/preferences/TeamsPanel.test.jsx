import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TeamsPanel } from '../../../components/preferences/TeamsPanel'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [], isLoading: false }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() })
}))

describe('TeamsPanel', () => {
  it('renders team management headers', () => {
    render(<TeamsPanel />)
    expect(screen.getByText(/Analyst Teams/i)).toBeInTheDocument()
  })
})
