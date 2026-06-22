import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { AttackChain } from '../../components/common/AttackChain'

describe('AttackChain Component', () => {
  const chainData = [
    { tactic: 'Initial Access', time: 'T+0m', score: 0.5, log_type: 'network' },
    { tactic: 'Execution', time: 'T+2m', score: 0.85, log_type: 'process' },
    { tactic: 'Exfiltration', time: 'T+15m', score: 0.9, log_type: 'network' }
  ]

  it('renders stages in chronological order', () => {
    render(<AttackChain chainData={chainData} />)
    expect(screen.getByText('Initial Access')).toBeInTheDocument()
    expect(screen.getByText('Execution')).toBeInTheDocument()
    expect(screen.getByText('Exfiltration')).toBeInTheDocument()
  })

  it('highlights fast progression with red connector', () => {
    render(<AttackChain chainData={chainData} />)
    // T+0m to T+2m is fast (< 5 mins), should render 'FAST' text
    expect(screen.getByText('FAST')).toBeInTheDocument()
  })

  it('displays time offset for each stage', () => {
    render(<AttackChain chainData={chainData} />)
    expect(screen.getByText('T+0m')).toBeInTheDocument()
    expect(screen.getByText('T+2m')).toBeInTheDocument()
    expect(screen.getByText('T+15m')).toBeInTheDocument()
  })

  it('empty array shows graceful message', () => {
    render(<AttackChain chainData={[]} />)
    expect(screen.getByText(/No attack chain data available/i)).toBeInTheDocument()
  })
})
