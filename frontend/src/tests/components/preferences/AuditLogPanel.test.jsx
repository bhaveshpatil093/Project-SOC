import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AuditLogPanel } from '../../../components/preferences/AuditLogPanel'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [], isLoading: false }),
}))

describe('AuditLogPanel', () => {
  it('renders audit logs', () => {
    render(<AuditLogPanel />)
    expect(screen.getByText(/No audit logs found/i)).toBeInTheDocument()
  })
})
