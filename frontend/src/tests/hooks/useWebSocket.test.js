import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWebSocket } from '../../hooks/useWebSocket'
import { useAlertStore } from '../../store/alertStore'

vi.mock('../../store/bannerStore', () => ({
  useBannerStore: {
    getState: () => ({ addBanner: vi.fn() })
  }
}))
const mockNotify = vi.fn()
vi.mock('../../hooks/useNotifications', () => ({
  useNotifications: () => ({ notify: mockNotify })
}))

describe('useWebSocket Hook', () => {
  let mockWebSocketInstance

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    useAlertStore.setState({ alerts: [], total: 0, pageSize: 50 })

    mockWebSocketInstance = {
      close: vi.fn()
    }
    
    vi.stubGlobal('WebSocket', vi.fn().mockImplementation(function() { return mockWebSocketInstance }))
  })

  it('connects on mount when authenticated', () => {
    const { result } = renderHook(() => useWebSocket(true))
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/alerts')
    
    act(() => {
      mockWebSocketInstance.onopen()
    })
    
    expect(result.current.connected).toBe(true)
  })

  it('does not connect when not authenticated', () => {
    renderHook(() => useWebSocket(false))
    expect(global.WebSocket).not.toHaveBeenCalled()
  })

  it('handles new_alert message type', () => {
    renderHook(() => useWebSocket(true))
    
    act(() => {
      mockWebSocketInstance.onmessage({
        data: JSON.stringify({ type: 'new_alert', data: { id: 'alt1', threat_level: 'critical' } })
      })
    })
    
    const storeState = useAlertStore.getState()
    expect(storeState.alerts).toHaveLength(1)
    expect(storeState.alerts[0].id).toBe('alt1')
  })

  it('reconnects after disconnect with backoff', () => {
    const { result } = renderHook(() => useWebSocket(true))
    
    act(() => {
      mockWebSocketInstance.onclose()
    })
    
    expect(result.current.connected).toBe(false)
    expect(result.current.reconnecting).toBe(true)
    
    // Initial connection call + 1 reconnect attempt
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    
    expect(global.WebSocket).toHaveBeenCalledTimes(2)
  })

  it('stops reconnecting after max retries', () => {
    renderHook(() => useWebSocket(true))
    
    // trigger 11 closes
    for (let i = 0; i < 11; i++) {
      act(() => {
        mockWebSocketInstance.onclose()
        vi.runAllTimers()
      })
    }
    
    // Initial call (1) + 10 retries (10) = 11 calls. The 11th onclose shouldn't trigger a 12th call.
    expect(global.WebSocket).toHaveBeenCalledTimes(11)
  })
})
