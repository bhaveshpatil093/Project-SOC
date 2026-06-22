import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Alerts } from '../pages/Alerts'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'

vi.mock('@tanstack/react-virtual', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useVirtualizer: () => ({
      getVirtualItems: () => [
        { index: 0, size: 50, start: 0 },
        { index: 1, size: 50, start: 50 },
        { index: 2, size: 50, start: 100 },
        { index: 3, size: 50, start: 150 },
        { index: 4, size: 50, start: 200 }
      ],
      getTotalSize: () => 250,
    })
  }
})

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Alerts List DataGrid Tests', () => {
  it('fetches MSW mocked alerts rendering the signature name natively', async () => {
    render(<Alerts />, { wrapper: createWrapper() })

    const elements = await screen.findAllByText(/admin/i)
    expect(elements.length).toBeGreaterThan(0)
  })

  it('filters data seamlessly without network crashes', async () => {
    render(<Alerts />, { wrapper: createWrapper() })

    const elements = await screen.findAllByText(/admin/i)
    expect(elements.length).toBeGreaterThan(0)

    const searchInput = screen.getByPlaceholderText(/Enter username.../i)
    expect(searchInput).toBeInTheDocument()

    // Type query to simulate user input bounding
    const user = userEvent.setup()
    await user.type(searchInput, 'admin')

    // React query should gracefully not break
    expect(searchInput).toHaveValue('admin')
  })
})
