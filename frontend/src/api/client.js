import axios from 'axios';

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export const isApiError = (err) => err instanceof ApiError;

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
});

let memoryToken = null;

export const setAuthToken = (token) => {
  memoryToken = token;
};

// Request Interceptor
apiClient.interceptors.request.use(config => {
  if (!config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json';
  }
  if (memoryToken) {
    config.headers.Authorization = `Bearer ${memoryToken}`;
  }
  return config;
});

// Response Interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;
    
    // Retry Logic for 5xx or Network Errors (once)
    if ((!error.response || error.response.status >= 500) && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      await new Promise(resolve => setTimeout(resolve, 1000));
      return apiClient(originalRequest);
    }
    
    let message = "Network Error";
    let status = 0;
    let detail = null;
    
    if (error.response) {
      status = error.response.status;
      detail = error.response.data;
      
      // Attempt to extract detail cleanly from standard FastAPI HTTPException signatures
      if (typeof error.response.data?.detail === 'string') {
        message = error.response.data.detail;
      } else if (error.response.data?.message) {
        message = error.response.data.message;
      } else if (Array.isArray(error.response.data?.detail)) {
        // FastAPI Pydantic validation error array
        message = error.response.data.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
      } else {
        message = `API Error ${status}`;
      }
    } else if (error.request) {
      message = "No response received from the server. Check your connection.";
    } else {
      message = error.message;
    }
    
    throw new ApiError(message, status, detail);
  }
);
