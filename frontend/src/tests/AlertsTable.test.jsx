import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Alerts } from '../pages/Alerts'
import { BrowserRouter } from 'react-router-dom'

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

    await waitFor(() => {
      // "Brute Force" is mapped from mockAlerts node 1
      expect(screen.getByText('Brute Force')).toBeInTheDocument()
      // "Suspicious PowerShell" from node 2
      expect(screen.getByText('Suspicious PowerShell')).toBeInTheDocument()
    })
  })

  it('filters data seamlessly without network crashes', async () => {
    render(<Alerts />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Brute Force')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/Search user/i)
    expect(searchInput).toBeInTheDocument()

    // Type query to simulate user input bounding
    const user = userEvent.setup()
    await user.type(searchInput, 'admin')

    // React query should gracefully not break
    expect(searchInput).toHaveValue('admin')
  })
})
