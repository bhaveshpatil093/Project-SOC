import os

tests = {
    "CorrelationGraph.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CorrelationGraph } from '../../../components/common/CorrelationGraph'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: { nodes: [], links: [] }, isLoading: false }),
}))

// Mock ResizeObserver
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('CorrelationGraph', () => {
  it('renders graph component', () => {
    const { container } = render(<CorrelationGraph alertId="1" />)
    expect(container).toBeInTheDocument()
  })
})
""",
    "DataTable.test.jsx": """import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DataTable } from '../../../components/common/DataTable'

describe('DataTable', () => {
  it('renders table headers', () => {
    const columns = [
      { key: 'id', label: 'ID' },
      { key: 'name', label: 'Name' },
    ]
    const data = [{ id: '1', name: 'Test' }]
    render(<DataTable columns={columns} data={data} />)
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
"""
}

os.makedirs('src/tests/components/common', exist_ok=True)

for filename, content in tests.items():
    with open(f"src/tests/components/common/{filename}", "w") as f:
        f.write(content)
