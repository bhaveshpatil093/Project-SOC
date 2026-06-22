import { describe, it, expect, beforeEach } from 'vitest'
import { useAlertStore } from '../../store/alertStore'

describe('alertStore', () => {
  beforeEach(() => {
    // Reset state before each test
    useAlertStore.setState({
      alerts: [],
      total: 0,
      filters: { status: '', threat_level: '', host_id: '', user_name: '', from_time: '', to_time: '' },
      page: 1,
    })
  })

  it('setFilters updates state correctly and resets page to 0', () => {
    const store = useAlertStore.getState()
    
    // Initial state
    expect(store.page).toBe(1)
    
    store.setFilters({ status: 'closed', threat_level: 'critical' })
    
    const updatedStore = useAlertStore.getState()
    expect(updatedStore.filters.status).toBe('closed')
    expect(updatedStore.filters.threat_level).toBe('critical')
    expect(updatedStore.page).toBe(0) // page reset
  })

  it('clearFilters resets to defaults', () => {
    const store = useAlertStore.getState()
    store.setFilters({ status: 'open', threat_level: 'high' })
    store.setPage(5)
    
    // act
    useAlertStore.getState().clearFilters()
    
    const clearedStore = useAlertStore.getState()
    expect(clearedStore.filters.status).toBe('')
    expect(clearedStore.filters.threat_level).toBe('')
    expect(clearedStore.page).toBe(0)
  })

  it('updateAlertStatus modifies single alert in list', () => {
    const store = useAlertStore.getState()
    store.setAlerts([
      { id: '1', alert_status: 'open' },
      { id: '2', alert_status: 'open' }
    ], 2)
    
    useAlertStore.getState().updateAlertStatus('1', 'resolved')
    
    const updatedStore = useAlertStore.getState()
    expect(updatedStore.alerts[0].alert_status).toBe('resolved')
    expect(updatedStore.alerts[1].alert_status).toBe('open')
  })

  it('setPage updates pagination state', () => {
    const store = useAlertStore.getState()
    store.setPage(3)
    expect(useAlertStore.getState().page).toBe(3)
  })
})
