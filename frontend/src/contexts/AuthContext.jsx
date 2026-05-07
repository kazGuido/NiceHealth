import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('auth_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if we have a token and validate it
    if (token) {
      validateToken();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const validateToken = async () => {
    try {
      const userData = await authApi.getCurrentUser(token);
      setUser(userData);
    } catch (error) {
      // Token is invalid, clear it
      logout();
    } finally {
      setLoading(false);
    }
  };

  const register = async (email) => {
    const response = await authApi.register(email);
    return response;
  };

  const requestPin = async (email) => {
    const response = await authApi.requestPin(email);
    return response;
  };

  const verifyPin = async (email, pinCode) => {
    const response = await authApi.verifyPin(email, pinCode);
    if (response.access_token) {
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem('auth_token', response.access_token);
      return response;
    }
    throw new Error('No token received');
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  const isAdmin = () => user?.role === 'admin';
  const isCustomer = () => user?.role === 'customer' || user?.role === 'admin';
  const isRetail = () => user?.role === 'retail' || user?.role === 'admin';

  const value = {
    user,
    token,
    loading,
    register,
    requestPin,
    verifyPin,
    logout,
    isAdmin,
    isCustomer,
    isRetail,
    role: user?.role || null,
    isAuthenticated: !!token && !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};


