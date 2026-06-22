import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MitrePanel } from '../../components/common/MitrePanel'

describe('MitrePanel Component', () => {
  it('renders all tactics as pills', () => {
    const tactics = ['Execution', 'Persistence']
    render(<MitrePanel tactics={tactics} />)
    expect(screen.getByText('Execution')).toBeInTheDocument()
    expect(screen.getByText('Persistence')).toBeInTheDocument()
  })

  it('renders technique IDs', () => {
    const techniques = ['T1059', 'T1053.005']
    render(<MitrePanel techniques={techniques} />)
    expect(screen.getByText('T1059')).toBeInTheDocument()
    expect(screen.getByText('T1053.005')).toBeInTheDocument()
  })

  it('technique links point to attack.mitre.org', () => {
    const techniques = ['T1059', 'T1053.005']
    render(<MitrePanel techniques={techniques} />)
    
    const t1059 = screen.getByText('T1059')
    expect(t1059.closest('a')).toHaveAttribute('href', 'https://attack.mitre.org/techniques/T1059')
    
    // Sub-techniques replace dot with slash
    const t1053 = screen.getByText('T1053.005')
    expect(t1053.closest('a')).toHaveAttribute('href', 'https://attack.mitre.org/techniques/T1053/005')
  })

  it('empty tactics array renders gracefully', () => {
    render(<MitrePanel tactics={[]} techniques={[]} />)
    expect(screen.getByText('No MITRE ATT&CK alignments detected.')).toBeInTheDocument()
  })
})
