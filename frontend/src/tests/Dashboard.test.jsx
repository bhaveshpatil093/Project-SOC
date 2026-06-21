import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Dashboard } from '../pages/Dashboard'
import { BrowserRouter } from 'react-router-dom'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Dashboard Integration Tests', () => {
  it('renders loading states securely prior to MSW resolution', () => {
    render(<Dashboard />, { wrapper: createWrapper() })
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('renders MSW fetched data directly onto stat cards', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    // mockAlertStats contains total_open: 4, critical_count: 2
    await waitFor(() => {
      // Check total open count maps to DOM
      expect(screen.getByText('4')).toBeInTheDocument()
      // Check critical count
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })
})
