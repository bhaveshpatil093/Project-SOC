import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ErrorBanner } from '../../components/common/ErrorBanner'

describe('ErrorBanner', () => {
  it('renders the given message', () => {
    render(<ErrorBanner message="Test error message" />)
    expect(screen.getByText('Test error message')).toBeInTheDocument()
  })

  it('renders default message if none provided', () => {
    render(<ErrorBanner message="" />)
    expect(screen.getByText('An unexpected network or system error occurred.')).toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn()
    render(<ErrorBanner message="Failed" onRetry={onRetry} />)
    const btn = screen.getByRole('button', { name: /retry connection/i })
    fireEvent.click(btn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
