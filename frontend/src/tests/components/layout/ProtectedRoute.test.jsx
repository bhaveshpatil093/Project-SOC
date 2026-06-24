import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProtectedRoute } from '../../../components/layout/ProtectedRoute'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom'
import * as AuthContextModule from '../../../contexts/AuthContext'

describe('ProtectedRoute', () => {
  const renderWithAuth = (isAuthenticated, isLoading) => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({ isAuthenticated, isLoading })
    return render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )
  }

  it('shows loading state', () => {
    renderWithAuth(false, true)
    expect(screen.getByText('Verifying authorization protocols...')).toBeInTheDocument()
  })

  it('redirects to login if not authenticated', () => {
    renderWithAuth(false, false)
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('renders outlet content if authenticated', () => {
    renderWithAuth(true, false)
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })
})
