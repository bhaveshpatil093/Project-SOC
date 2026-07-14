import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { apiClient, setAuthToken } from '../api/client'

const AuthContext = createContext(null)

const SESSION_TOKEN_KEY = 'soc_auth_token'
const SESSION_USER_KEY = 'soc_auth_user'

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const login = async (username, password) => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const res = await apiClient.post('/api/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })

      if (res.access_token) {
        // Persist token in sessionStorage so page refresh doesn't log the user out
        sessionStorage.setItem(SESSION_TOKEN_KEY, res.access_token)
        if (res.user) {
          sessionStorage.setItem(SESSION_USER_KEY, JSON.stringify(res.user))
        }

        setAuthToken(res.access_token)
        setUser(res.user)
        setIsAuthenticated(true)
        return { success: true }
      }
      return { success: false, error: 'Token not received from server' }
    } catch (err) {
      return {
        success: false,
        error: err.message || 'Authentication failed. Check backend connection.',
        code: err.code,
        fields: err.fields,
      }
    }
  }

  const logout = async () => {
    try {
      await apiClient.post('/api/auth/logout')
    } catch (e) {
      console.warn('Logout ping failed gracefully.')
    } finally {
      sessionStorage.removeItem(SESSION_TOKEN_KEY)
      sessionStorage.removeItem(SESSION_USER_KEY)
      setAuthToken(null)
      setUser(null)
      setIsAuthenticated(false)
    }
  }

  const fetchCurrentUser = useCallback(async () => {
    // Check sessionStorage for a persisted token from previous page load
    const persistedToken = sessionStorage.getItem(SESSION_TOKEN_KEY)
    const persistedUser = sessionStorage.getItem(SESSION_USER_KEY)

    if (persistedToken) {
      // Restore the token into the in-memory store so axios sends it
      setAuthToken(persistedToken)

      if (persistedUser) {
        try {
          setUser(JSON.parse(persistedUser))
          setIsAuthenticated(true)
          setIsLoading(false)
          // Validate the token is still good in the background
          try {
            const res = await apiClient.get('/api/auth/me')
            setUser(res)
            setIsAuthenticated(true)
          } catch {
            // Token expired — clear and redirect to login
            sessionStorage.removeItem(SESSION_TOKEN_KEY)
            sessionStorage.removeItem(SESSION_USER_KEY)
            setAuthToken(null)
            setUser(null)
            setIsAuthenticated(false)
          }
          return
        } catch {
          // JSON parse failed — fall through to /me request
        }
      }
    }

    // No persisted token — try /me endpoint (will fail gracefully if no token)
    try {
      const res = await apiClient.get('/api/auth/me')
      setUser(res)
      setIsAuthenticated(true)
    } catch (e) {
      setAuthToken(null)
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
