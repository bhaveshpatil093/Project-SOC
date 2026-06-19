import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { apiClient, setAuthToken } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const login = async (username, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const res = await apiClient.post('/api/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      if (res.access_token) {
        setAuthToken(res.access_token);
        setUser(res.user);
        setIsAuthenticated(true);
        return { success: true };
      }
      return { success: false, error: 'Token not mapped successfully' };
    } catch (err) {
      return { 
        success: false, 
        error: err.response?.data?.detail || 'Authentication handshake completely failed.'
      };
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/api/auth/logout');
    } catch (e) {
      console.warn("Logout ping failed gracefully.");
    } finally {
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const fetchCurrentUser = useCallback(async () => {
    // If we have no token, no point calling /me (page refresh drops memory state)
    let currentToken = null;
    try {
        const { apiClient } = await import('../api/client');
        // Actually we don't have access to memoryToken directly exported from client.js 
        // We can just try and let it fail or we can use another trick.
        const res = await apiClient.get('/api/auth/me');
        setUser(res);
        setIsAuthenticated(true);
    } catch (e) {
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
