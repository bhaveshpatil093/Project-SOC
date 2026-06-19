import { http, HttpResponse } from 'msw';
import { mockAlerts, mockAlertStats, mockFeedbackStats, mockTrainingHistory } from './data';

export const handlers = [
  http.get('http://localhost:8000/api/alerts/stats', () => {
    return HttpResponse.json(mockAlertStats);
  }),
  http.get('http://localhost:8000/api/alerts', () => {
    return HttpResponse.json({ data: mockAlerts, total: mockAlerts.length, page: 0, page_size: 50 });
  }),
  http.get('http://localhost:8000/api/alerts/:id', ({ params }) => {
    const alert = mockAlerts.find(a => a.id === params.id) || mockAlerts[0];
    return HttpResponse.json({ 
      ...alert, 
      shap_values: { "bytes_out": 0.2, "failed_logins": 0.5 },
      human_explanation: "This alert triggered due to excessive failed logins."
    });
  }),
  http.get('http://localhost:8000/api/feedback/stats', () => {
    return HttpResponse.json(mockFeedbackStats);
  }),
  http.get('http://localhost:8000/api/training/history', () => {
    return HttpResponse.json(mockTrainingHistory);
  }),
  http.get('http://localhost:8000/health', () => {
    return HttpResponse.json({ status: "ok" });
  }),
  http.post('http://localhost:8000/api/feedback', () => {
    return HttpResponse.json({ status: "submitted" });
  }),
  http.post('http://localhost:8000/api/alerts/trigger-scoring', () => {
    return HttpResponse.json({ scored: 100, alerts_above_threshold: 5 });
  }),
  http.patch('http://localhost:8000/api/alerts/:id/status', async ({ request }) => {
    const data = await request.json();
    return HttpResponse.json({ status: "success", new_status: data.status });
  })
];
