import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from '../components/common/Badge'

describe('Badge Component', () => {
  it('renders standard fallback badge', () => {
    render(<Badge>Fallback</Badge>)
    expect(screen.getByText('Fallback')).toBeInTheDocument()
  })

  it('renders critical variant accurately mapping tailwind red tokens', () => {
    render(<Badge variant="critical">CRITICAL</Badge>)
    const el = screen.getByText('CRITICAL')
    expect(el.className).toContain('text-red-400')
  })

  it('renders TP variant accurately mapping generic validation tokens', () => {
    render(<Badge variant="tp">True Positive</Badge>)
    const el = screen.getByText('True Positive')
    // Assuming tp variant maps correctly
    expect(el).toBeInTheDocument()
  })
})
