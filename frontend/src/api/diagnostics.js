import { apiClient } from './client'

export const getKibanaHealth   = () => apiClient.get('/api/diagnostics/kibana-health')
export const getIndexStats     = () => apiClient.get('/api/diagnostics/index-stats')
export const getDataFreshness  = () => apiClient.get('/api/diagnostics/data-freshness')
export const getLocalDbStats   = () => apiClient.get('/api/diagnostics/local-db-stats')
export const testFetch = (index, minutes) =>
  apiClient.post('/api/diagnostics/test-fetch', {index, since_minutes: minutes})
