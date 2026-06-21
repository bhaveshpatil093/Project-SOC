import apiClient from './client';

export const getShiftReport = async (hours = 8) => {
    let endpoint = `/api/reports/shift?hours=${hours}`;
    if (hours === 24) endpoint = '/api/reports/daily';
    if (hours === 168) endpoint = '/api/reports/weekly';
    
    const response = await apiClient.get(endpoint);
    return response.data;
};
