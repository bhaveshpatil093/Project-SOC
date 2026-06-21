import { apiClient } from './client'

export const getEntities = async (params) => {
  const response = await apiClient.get('/api/entities', { params })
  return response.data
}

export const getEntityProfile = async (entityKey) => {
  const response = await apiClient.get(`/api/entities/${entityKey}`)
  return response.data
}

export const getEntityAlerts = async (entityKey, params) => {
  const response = await apiClient.get(`/api/entities/${entityKey}/alerts`, { params })
  return response.data
}

export const getWatchlist = async () => {
  const response = await apiClient.get('/api/entities/watchlist')
  return response.data
}

export const addToWatchlist = async (entityKey, reason) => {
  const response = await apiClient.post(`/api/entities/${entityKey}/watchlist`, { reason })
  return response.data
}

export const removeFromWatchlist = async (entityKey) => {
  const response = await apiClient.delete(`/api/entities/${entityKey}/watchlist`)
  return response.data
}

export const getEntityScoreHistory = async (entityKey, sinceHours = 168) => {
  const response = await apiClient.get(`/api/entities/${entityKey}/score-history`, {
    params: { since_hours: sinceHours },
  })
  return response.data
}

export const getEntityScoreTrends = async (entityKey) => {
  const response = await apiClient.get(`/api/entities/${entityKey}/score-trends`)
  return response.data
}

export const getSystemScoreTrends = async () => {
  const response = await apiClient.get('/api/entities/system/trends')
  return response.data
}
