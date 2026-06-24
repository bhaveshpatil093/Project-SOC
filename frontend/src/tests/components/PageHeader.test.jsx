import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PageHeader } from '../../components/common/PageHeader'

describe('PageHeader', () => {
  it('renders title and subtitle', () => {
    render(<PageHeader title="Dashboard" subtitle="Overview of system" />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Overview of system')).toBeInTheDocument()
  })

  it('renders action elements if provided', () => {
    render(<PageHeader title="Test" actions={<button>Click Me</button>} />)
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument()
  })
})
