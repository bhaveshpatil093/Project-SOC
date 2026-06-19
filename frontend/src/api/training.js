import { apiClient } from './client';

export const startInitialTraining = () => apiClient.post('/api/training/initial');
export const startRetraining = () => apiClient.post('/api/training/retrain');
export const getTrainingStatus = (job_id) => apiClient.get(`/api/training/status/${job_id}`);
export const getTrainingHistory = () => apiClient.get('/api/training/history');
