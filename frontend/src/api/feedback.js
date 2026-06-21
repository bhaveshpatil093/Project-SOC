import { apiClient } from './client'

export const submitFeedback = (data) => apiClient.post('/api/feedback', data)
export const getFeedback = (params) => apiClient.get('/api/feedback', { params })
export const getFeedbackStats = () => apiClient.get('/api/feedback/stats')
export const getSuppressionRules = () => apiClient.get('/api/feedback/suppression-rules')

// Legacy backwards compatibility aliases
export const fetchFeedbackStats = getFeedbackStats

export const getLabelingQueue = (params) =>
  apiClient.get('/api/feedback/labeling-queue', { params })
export const getLabelingStats = () => apiClient.get('/api/feedback/labeling-stats')
