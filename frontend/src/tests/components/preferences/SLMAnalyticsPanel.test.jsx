import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SLMAnalyticsPanel } from '../../../components/preferences/SLMAnalyticsPanel'

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ 
    data: { 
      trends: {
        query_type_distribution: {},
        daily_queries: [],
        peak_hour: 14,
        quality_score_trend: [],
        avg_response_time_trend: []
      },
      top_questions: [],
      knowledge_gaps: [],
      most_investigated: []
    }, 
    isLoading: false 
  }),
}))
vi.mock('../../../store/uiStore', () => ({
  useUiStore: () => ({ setSomething: vi.fn() })
}))
vi.mock('../../../store/slmStore', () => ({
  useSlmStore: () => ({ fetchStatus: vi.fn(), isInitializing: false })
}))

describe('SLMAnalyticsPanel', () => {
  it('renders model analytics headers', () => {
    render(<SLMAnalyticsPanel />)
    expect(screen.getByText(/Total Queries \(30d\)/i)).toBeInTheDocument()
  })
})
