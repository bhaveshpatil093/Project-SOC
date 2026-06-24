import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PlatformHealthDropdown } from '../../../components/layout/PlatformHealthDropdown'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: { status: 'healthy', version: '1.0.0' },
    isLoading: false,
    isError: false,
  }),
}))

describe('PlatformHealthDropdown', () => {
  it('renders health status', () => {
    render(<PlatformHealthDropdown />)
    expect(screen.getByText('Operational')).toBeInTheDocument()
  })
})
