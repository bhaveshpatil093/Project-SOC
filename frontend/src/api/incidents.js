import { apiClient } from './client';

export const getIncidents = async ({ status, attack_stage, threat_level, host_id, limit = 20, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (attack_stage) params.append('attack_stage', attack_stage);
  if (threat_level) params.append('threat_level', threat_level);
  if (host_id) params.append('host_id', host_id);
  params.append('limit', limit);
  params.append('offset', offset);
  
  return await apiClient.get(`/api/incidents?${params.toString()}`);
};

export const getIncidentDetail = async (incidentId) => {
  return await apiClient.get(`/api/incidents/${incidentId}`);
};

export const updateIncidentStatus = async (incidentId, status, notes = null) => {
  return await apiClient.patch(`/api/incidents/${incidentId}/status`, { status, notes });
};

export const escalateIncident = async (incidentId, escalated_to, reason) => {
  return await apiClient.post(`/api/incidents/${incidentId}/escalate`, { escalated_to, reason });
};

export const getIncidentStats = async () => {
  return await apiClient.get('/api/incidents/stats');
};

export const investigateIncident = async (incidentId) => {
  return await apiClient.get(`/api/incidents/${incidentId}/investigate`);
};


export const generateIncidentReport = async (incidentId) => {
    const response = await apiClient.post(`/api/incidents/${incidentId}/generate-report`);
    return response.data;
};

export const getIncidentReport = async (incidentId) => {
    const response = await apiClient.get(`/api/incidents/${incidentId}/report`);
    return response.data;
};
