import { apiClient } from './client';

export const sendMessage = async (message, alert_id, conversation_id) => {
    const payload = { message };
    if (alert_id) payload.alert_id = alert_id;
    if (conversation_id) payload.conversation_id = conversation_id;
    
    const response = await apiClient.post('/api/slm/chat', payload);
    return response.data;
};

export const explainAlert = async (alert_id) => {
    const response = await apiClient.post(`/api/slm/explain/${alert_id}`);
    return response.data;
};

export const getSlmStatus = async () => {
    const response = await apiClient.get('/api/slm/status');
    return response.data;
};

export const clearConversation = async (conversation_id) => {
    const response = await apiClient.delete(`/api/slm/conversations/${conversation_id}`);
    return response.data;
};
