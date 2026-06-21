import { apiClient } from './client'

export const getAlerts = (params) => apiClient.get('/api/alerts', { params })
export const getAlert = (id) => apiClient.get(`/api/alerts/${id}`)
export const getAlertStats = () => apiClient.get('/api/alerts/stats')
export const getAlertTimeline = (id) => apiClient.get(`/api/alerts/${id}/timeline`)
export const updateAlertStatus = (id, status) =>
  apiClient.patch(`/api/alerts/${id}/status`, { status })
export const triggerScoring = () => apiClient.post('/api/alerts/trigger-scoring')

// Aliases for backwards compatibility during refactor
export const fetchAlerts = getAlerts
export const fetchAlert = getAlert
export const fetchAlertStats = getAlertStats
export const fetchAlertTimeline = getAlertTimeline


export const addTags = async (alert_id, tags) => {
  const response = await apiClient.post(`/api/alerts/${alert_id}/tags`, { tags })
  return response.data
}

export const removeTag = async (alert_id, tag) => {
  const response = await apiClient.delete(`/api/alerts/${alert_id}/tags/${tag}`)
  return response.data
}

export const getAllTags = async () => {
  const response = await apiClient.get('/api/alerts/tags')
  return response.data
}
