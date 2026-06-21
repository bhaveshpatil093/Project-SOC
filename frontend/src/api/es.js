import apiClient from './client';

export const getKibanaUrl = async () => {
    const response = await apiClient.get('/api/kibana/url');
    return response.data;
};

export const getEsIndices = async () => {
    const response = await apiClient.get('/api/es/indices');
    return response.data;
};

export const runEsQuery = async (payload) => {
    const response = await apiClient.post('/api/es/query', payload);
    return response.data;
};
