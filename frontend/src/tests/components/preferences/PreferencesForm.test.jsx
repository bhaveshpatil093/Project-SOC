import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PreferencesForm } from '../../../components/preferences/PreferencesForm'

vi.mock('../../../store/preferencesStore', () => ({
  usePreferencesStore: () => ({
    theme: 'dark',
    defaultView: 'dashboard',
    autoRefresh: true,
    alertColumns: { host: true, score: true, rule: true },
    setPreference: vi.fn(),
  }),
}))

describe('PreferencesForm', () => {
  it('renders correctly', () => {
    render(<PreferencesForm />)
    expect(screen.getByText(/Analyst Preferences/i)).toBeInTheDocument()
  })
})
