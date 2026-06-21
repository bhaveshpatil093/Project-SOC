import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ThreatGauge } from '../components/common/ThreatGauge'

describe('ThreatGauge SVG Engine Component', () => {
  it('renders critical score natively checking fallback DOM tokens', async () => {
    render(<ThreatGauge score={85} />)

    await waitFor(
      () => {
        expect(screen.getByText('85')).toBeInTheDocument()
        expect(screen.getByText('Critical')).toBeInTheDocument()
      },
      { timeout: 2000 },
    )
  })

  it('renders low bounds securely', async () => {
    render(<ThreatGauge score={25} />)

    await waitFor(
      () => {
        expect(screen.getByText('25')).toBeInTheDocument()
        expect(screen.getByText('Low')).toBeInTheDocument()
      },
      { timeout: 2000 },
    )
  })
})
