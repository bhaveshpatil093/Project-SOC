import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BackupsPanel } from '../../../components/preferences/BackupsPanel'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [], isLoading: false }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() })
}))

describe('BackupsPanel', () => {
  it('renders backups header', () => {
    render(<BackupsPanel />)
    expect(screen.getByText(/Elasticsearch Snapshots/i)).toBeInTheDocument()
  })
})
