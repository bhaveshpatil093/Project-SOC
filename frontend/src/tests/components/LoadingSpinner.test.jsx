import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'

describe('LoadingSpinner', () => {
  it('renders correctly with default props', () => {
    const { container } = render(<LoadingSpinner />)
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('h-8', 'w-8', 'border-blue-500')
    expect(container.firstChild).toHaveClass('flex', 'justify-center')
  })

  it('renders different sizes and colors', () => {
    const { container } = render(<LoadingSpinner size="lg" color="red" centered={false} />)
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('h-12', 'w-12', 'border-red-500')
    expect(container.firstChild).toBe(spinner) // not wrapped in centered div
  })
})
