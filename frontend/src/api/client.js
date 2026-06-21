import axios from 'axios'

export class ApiError extends Error {
  constructor(message, status, detail, code = null, fields = null, correlationId = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.code = code
    this.fields = fields
    this.correlationId = correlationId
  }
}

export const isApiError = (err) => err instanceof ApiError

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

let memoryToken = null

export const setAuthToken = (token) => {
  memoryToken = token
}

// Simple global toast utility for rate limits
const showRateLimitToast = (retryAfterSeconds) => {
  window.dispatchEvent(
    new CustomEvent('api-toast', {
      detail: {
        id: 'rate-limit-toast',
        title: 'Rate Limit Exceeded',
        message: `Too many requests — please wait ${retryAfterSeconds || 60}s`,
        level: 'critical',
        duration: 5000,
      },
    }),
  )
}

// Request Interceptor
apiClient.interceptors.request.use((config) => {
  if (!config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json'
  }
  if (memoryToken) {
    config.headers.Authorization = `Bearer ${memoryToken}`
  }
  return config
})

// Response Interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config

    // Retry Logic for 5xx or Network Errors (once)
    if (
      (!error.response || error.response.status >= 500) &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true
      await new Promise((resolve) => setTimeout(resolve, 1000))
      return apiClient(originalRequest)
    }

    // Handle 429 Rate Limit specifically
    if (error.response && error.response.status === 429) {
      const retryAfter = error.response.headers['retry-after'] || 60
      showRateLimitToast(retryAfter)
      throw new ApiError(
        `Rate limit exceeded. Please wait ${retryAfter} seconds.`,
        429,
        error.response.data,
      )
    }

    let message = 'Network Error'
    let status = 0
    let detail = null
    let code = 'UNKNOWN_ERROR'
    let fields = null
    let correlationId = null

    if (error.response) {
      status = error.response.status
      detail = error.response.data

      // If it matches our new structured JSONResponse format
      if (detail && typeof detail === 'object' && detail.error) {
        code = detail.error
        message = detail.message || message
        fields = detail.fields || null
        correlationId = detail.correlation_id || null
      } else {
        // Attempt to extract detail cleanly from standard FastAPI HTTPException signatures
        if (typeof detail?.detail === 'string') {
          message = detail.detail
        } else if (detail?.message) {
          message = detail.message
        } else if (Array.isArray(detail?.detail)) {
          // FastAPI Pydantic validation error array
          message = detail.detail.map((d) => `${d.loc.join('.')}: ${d.msg}`).join(', ')
        } else {
          message = `API Error ${status}`
        }
      }
    } else if (error.request) {
      message = 'No response received from the server. Check your connection.'
      code = 'NETWORK_ERROR'
    } else {
      message = error.message
    }

    throw new ApiError(message, status, detail, code, fields, correlationId)
  },
)
