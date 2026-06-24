import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'

describe('ConfirmDialog', () => {
  it('does not render when isOpen is false', () => {
    render(<ConfirmDialog isOpen={false} title="Test" message="Msg" onConfirm={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.queryByText('Test')).not.toBeInTheDocument()
  })

  it('renders and responds to buttons when open', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(<ConfirmDialog isOpen={true} title="Dialog Title" message="Are you sure?" onConfirm={onConfirm} onCancel={onCancel} confirmLabel="Yes" />)
    
    expect(screen.getByText('Dialog Title')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
    
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
    
    fireEvent.click(screen.getByText('Yes'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
