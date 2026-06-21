import { apiClient } from './client'

export const sendMessage = async (message, alert_id, incident_id, conversation_id) => {
  const payload = { message }
  if (alert_id) payload.alert_id = alert_id
  if (incident_id) payload.incident_id = incident_id
  if (conversation_id) payload.conversation_id = conversation_id

  const response = await apiClient.post('/api/slm/chat', payload)
  return response.data
}

export const explainAlert = async (alert_id) => {
  const response = await apiClient.post(`/api/slm/explain/${alert_id}`)
  return response.data
}

export const getSlmStatus = async () => {
  const response = await apiClient.get('/api/slm/status')
  return response.data
}

export const clearConversation = async (conversation_id) => {
  const response = await apiClient.delete(`/api/slm/conversations/${conversation_id}`)
  return response.data
}

export const getModelInfo = async () => {
  const response = await apiClient.get('/api/slm/model-info')
  return response.data
}

export const reloadModel = async (model) => {
  const response = await apiClient.post('/api/slm/reload-model', { model })
  return response.data
}

export const getRagStats = async () => {
  const response = await apiClient.get('/api/slm/rag/stats')
  return response.data
}

export const reindexRag = async () => {
  const response = await apiClient.post('/api/slm/rag/reindex')
  return response.data
}

export const clearRagIndex = async () => {
  const response = await apiClient.delete('/api/slm/rag/clear?confirm=yes')
  return response.data
}

export const getSlmMetrics = async (sinceHours = 24) => {
  const response = await apiClient.get(`/api/slm/metrics?since_hours=${sinceHours}`)
  return response.data
}

export const getAlertPlaybook = async (alertId) => {
  const response = await apiClient.get(`/api/slm/playbook/${alertId}`)
  return response.data
}
