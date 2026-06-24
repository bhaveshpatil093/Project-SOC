import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatCard } from '../../components/common/StatCard'

describe('StatCard', () => {
  it('renders title, value and icon', () => {
    const Icon = () => <svg data-testid="test-icon" />
    render(<StatCard title="Total Users" value="1,024" icon={Icon} subtitle="5% increase" />)
    
    expect(screen.getByText('Total Users')).toBeInTheDocument()
    expect(screen.getByText('1,024')).toBeInTheDocument()
    expect(screen.getByTestId('test-icon')).toBeInTheDocument()
    expect(screen.getByText('5% increase')).toBeInTheDocument()
  })

  it('renders loading state correctly', () => {
    const { container } = render(<StatCard title="Errors" loading={true} />)
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })
})
