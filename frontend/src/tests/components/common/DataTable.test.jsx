import React from 'react'
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
