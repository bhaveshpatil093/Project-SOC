import os

tests = {
    "AuditLogPanel.test.jsx": """import React from 'react'
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
""",
    "BackupsPanel.test.jsx": """import React from 'react'
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
"""
}

for filename, content in tests.items():
    with open(f"src/tests/components/preferences/{filename}", "w") as f:
        f.write(content)
