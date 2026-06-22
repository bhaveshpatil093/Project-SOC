import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAlerts } from '../../hooks/useAlerts'
import * as api from '../../api/alerts'
import { useAlertStore } from '../../store/alertStore'

vi.mock('../../api/alerts')
vi.mock('../../store/preferencesStore', () => ({
  usePreferencesStore: () => ({
    alertsPageSize: 50,
    defaultAlertSort: 'timestamp',
    showLowAlerts: true
  })
}))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } }
})

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
)

describe('useAlerts Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
    useAlertStore.getState().setAlerts([], 0)
    useAlertStore.getState().clearFilters()
  })

  it('fetches alerts on mount', async () => {
    api.getAlerts.mockResolvedValueOnce({ alerts: [{ id: '1', threat_level: 'critical' }], total: 1 })
    
    const { result } = renderHook(() => useAlerts(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    
    expect(result.current.alerts).toHaveLength(1)
    expect(result.current.total).toBe(1)
    expect(api.getAlerts).toHaveBeenCalled()
  })

  it('refetches when filters change', async () => {
    api.getAlerts.mockResolvedValue({ alerts: [], total: 0 })
    const { result } = renderHook(() => useAlerts(), { wrapper })
    
    await waitFor(() => expect(result.current.loading).toBe(false))
    
    act(() => {
      result.current.setFilters({ status: 'open' })
    })
    
    await waitFor(() => {
      expect(api.getAlerts).toHaveBeenCalledTimes(2)
      // verify last call had the filter
      const lastCallArg = api.getAlerts.mock.calls[1][0]
      expect(lastCallArg.status).toBe('open')
    })
  })

  it('updateStatus optimistically updates local state', async () => {
    api.getAlerts.mockResolvedValueOnce({ alerts: [{ id: '1', status: 'open', threat_level: 'low' }], total: 1 })
    api.updateAlertStatus.mockResolvedValueOnce({ success: true })
    
    const { result } = renderHook(() => useAlerts(), { wrapper })
    
    await waitFor(() => expect(result.current.alerts).toHaveLength(1))
    
    act(() => {
      result.current.updateStatus({ id: '1', status: 'closed' })
    })
    
    await waitFor(() => {
      expect(api.updateAlertStatus).toHaveBeenCalledWith('1', 'closed')
      expect(result.current.alerts[0].status).toBe('closed')
    }, { timeout: 2000 })
  })

  it('handles API error state', async () => {
    api.getAlerts.mockRejectedValueOnce(new Error('Network Error'))
    
    const { result } = renderHook(() => useAlerts(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.error).toBe('Network Error')
      expect(result.current.loading).toBe(false)
    })
  })
})
