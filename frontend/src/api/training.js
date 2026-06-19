import { apiClient } from './client';

export const startInitialTraining = () => apiClient.post('/api/training/initial');
export const startRetraining = () => apiClient.post('/api/training/incremental');
export const getTrainingStatus = (job_id) => apiClient.get(`/api/training/status/${job_id}`);
export const getTrainingHistory = () => apiClient.get('/api/training/status');

// MLflow endpoints
export const getMlflowExperiments = () => apiClient.get('/api/training/mlflow/experiments');
export const getMlflowRuns = (experimentId) => apiClient.get(`/api/training/mlflow/runs/${experimentId}`);
export const getMlflowRunDetail = (runId) => apiClient.get(`/api/training/mlflow/runs/detail/${runId}`);
export const compareMlflowRuns = (runIds) => apiClient.get(`/api/training/mlflow/compare?run_ids=${runIds.join(',')}`);
