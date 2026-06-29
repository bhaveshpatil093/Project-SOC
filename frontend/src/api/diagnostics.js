import client from './client'

export const getKibanaHealth   = () => client.get('/api/diagnostics/kibana-health')
export const getIndexStats     = () => client.get('/api/diagnostics/index-stats')
export const getDataFreshness  = () => client.get('/api/diagnostics/data-freshness')
export const getLocalDbStats   = () => client.get('/api/diagnostics/local-db-stats')
export const testFetch = (index, minutes) =>
  client.post('/api/diagnostics/test-fetch', {index, since_minutes: minutes})
