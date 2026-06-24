import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { LogViewer } from '../../../components/system/LogViewer'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [], isLoading: false }),
}))

window.HTMLElement.prototype.scrollIntoView = vi.fn()

describe('LogViewer', () => {
  it('renders log viewer header', () => {
    render(<LogViewer />)
    expect(screen.getByText(/Log Console/i)).toBeInTheDocument()
  })
})
