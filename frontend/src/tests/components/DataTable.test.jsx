import React from 'react'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DataTable } from '../../components/common/DataTable'

describe('DataTable Component', () => {
  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'score', label: 'Score', sortable: true },
    { key: 'actions', label: 'Actions', render: (val, row) => <button>Click {row.name}</button> }
  ]

  const data = [
    { id: '1', name: 'Zebra', score: 90 },
    { id: '2', name: 'Alpha', score: 50 },
    { id: '3', name: 'Beta', score: 70 }
  ]

  it('renders correctly with data', () => {
    render(<DataTable columns={columns} data={data} />)
    expect(screen.getByText('Zebra')).toBeInTheDocument()
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
  })

  it('sorts rows when header clicked', () => {
    render(<DataTable columns={columns} data={data} />)
    const nameHeader = screen.getByText('Name')
    
    // Initial order is data insertion order
    let rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('Zebra')).toBeInTheDocument() // rows[0] is header
    
    // Click to sort ascending
    fireEvent.click(nameHeader)
    rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('Alpha')).toBeInTheDocument()
    expect(within(rows[2]).getByText('Beta')).toBeInTheDocument()
    expect(within(rows[3]).getByText('Zebra')).toBeInTheDocument()
  })

  it('toggles sort direction on second click', () => {
    render(<DataTable columns={columns} data={data} />)
    const scoreHeader = screen.getByText('Score')
    
    // Click once (ascending)
    fireEvent.click(scoreHeader)
    let rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('50')).toBeInTheDocument()
    
    // Click twice (descending)
    fireEvent.click(scoreHeader)
    rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('90')).toBeInTheDocument()
    expect(within(rows[3]).getByText('50')).toBeInTheDocument()
  })

  it('shows empty message when no data', () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Custom empty message" />)
    expect(screen.getByText('Custom empty message')).toBeInTheDocument()
  })

  it('renders custom cell renderer functions', () => {
    render(<DataTable columns={columns} data={data} />)
    expect(screen.getByRole('button', { name: 'Click Alpha' })).toBeInTheDocument()
  })
})
