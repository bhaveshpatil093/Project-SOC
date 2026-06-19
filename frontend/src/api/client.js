import axios from 'axios';

export class ApiError extends Error {
  constructor(message, status, detail, code = null, fields = null, correlationId = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.code = code;
    this.fields = fields;
    this.correlationId = correlationId;
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

// Simple global toast utility for rate limits
const showRateLimitToast = (retryAfterSeconds) => {
  const existing = document.getElementById('rate-limit-toast');
  if (existing) return;

  const toast = document.createElement('div');
  toast.id = 'rate-limit-toast';
  toast.className = 'fixed bottom-4 right-4 bg-red-600/90 backdrop-blur-md text-white px-6 py-4 rounded-xl shadow-2xl border border-red-500/30 z-[9999] flex items-center font-medium transition-all duration-300 transform translate-y-0 opacity-100';
  document.body.appendChild(toast);

  let secondsLeft = parseInt(retryAfterSeconds, 10) || 60;

  const updateText = () => {
    toast.innerHTML = `
      <svg class="w-5 h-5 mr-3 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
      Too many requests — please wait <span class="font-bold ml-1 w-6 text-center">${secondsLeft}</span>s
    `;
  };

  updateText();

  const interval = setInterval(() => {
    secondsLeft -= 1;
    if (secondsLeft <= 0) {
      clearInterval(interval);
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(100%)';
      setTimeout(() => toast.remove(), 300);
    } else {
      updateText();
    }
  }, 1000);
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
    
    // Handle 429 Rate Limit specifically
    if (error.response && error.response.status === 429) {
      const retryAfter = error.response.headers['retry-after'] || 60;
      showRateLimitToast(retryAfter);
      throw new ApiError(`Rate limit exceeded. Please wait ${retryAfter} seconds.`, 429, error.response.data);
    }
    
    let message = "Network Error";
    let status = 0;
    let detail = null;
    let code = "UNKNOWN_ERROR";
    let fields = null;
    let correlationId = null;
    
    if (error.response) {
      status = error.response.status;
      detail = error.response.data;
      
      // If it matches our new structured JSONResponse format
      if (detail && typeof detail === 'object' && detail.error) {
        code = detail.error;
        message = detail.message || message;
        fields = detail.fields || null;
        correlationId = detail.correlation_id || null;
      } else {
        // Attempt to extract detail cleanly from standard FastAPI HTTPException signatures
        if (typeof detail?.detail === 'string') {
          message = detail.detail;
        } else if (detail?.message) {
          message = detail.message;
        } else if (Array.isArray(detail?.detail)) {
          // FastAPI Pydantic validation error array
          message = detail.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
        } else {
          message = `API Error ${status}`;
        }
      }
    } else if (error.request) {
      message = "No response received from the server. Check your connection.";
      code = "NETWORK_ERROR";
    } else {
      message = error.message;
    }
    
    throw new ApiError(message, status, detail, code, fields, correlationId);
  }
);
