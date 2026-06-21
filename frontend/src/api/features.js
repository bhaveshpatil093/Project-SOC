import { apiClient } from './client'

export const runFeaturePipeline = () => apiClient.post('/api/features/run')
