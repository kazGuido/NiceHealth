import axios from 'axios';
import { setupCache } from 'axios-cache-interceptor';

// Use backend domain from environment or default to production domain
const API_URL = import.meta.env.VITE_API_URL || 'https://niceq.nicedaytech.com';

// Setup axios instance with caching
const axiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Wrap with cache logic (default 5 min cache for GET requests)
const api = setupCache(axiosInstance, {
  ttl: 1000 * 60 * 5, // 5 minutes
});

// Helper to clear cache when data is modified
const clearApiCache = () => {
  api.storage.remove('all');
};

// Add token to requests if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 errors (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      const isV2 = window.location.pathname.startsWith('/v2');
      window.location.href = isV2 ? '/v2/login' : '/login';
    }
    return Promise.reject(error);
  }
);

// Helper to get file URL through proxy
export const getFileUrl = (fileName) => {
  if (!fileName) return null;
  if (fileName.startsWith('http')) return fileName; // Already a full URL
  return `${API_URL}/files/${fileName}`;
};

// Authentication API
export const authApi = {
  register: async (email) => {
    const response = await api.post('/auth/register', { email });
    return response.data;
  },

  requestPin: async (email) => {
    const response = await api.post('/auth/request-pin', { email });
    return response.data;
  },

  verifyPin: async (email, pinCode) => {
    const response = await api.post('/auth/verify-pin', { email, pin_code: pinCode });
    return response.data;
  },

  getCurrentUser: async (token) => {
    const response = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  },
};

// Health Data API
export const healthDataApi = {
  // Get all measurements
  getMeasurements: async (page = 1, pageSize = 20, patientId = null, deviceId = null) => {
    const params = { page, page_size: pageSize };
    if (patientId) params.patient_id = patientId;
    if (deviceId) params.device_id = deviceId;
    const response = await api.get('/health-data/receive-measurement', { params });
    return response.data;
  },

  // Get single measurement
  getMeasurement: async (id) => {
    const response = await api.get(`/health-data/receive-measurement/${id}`);
    return response.data;
  },

  // Create measurement (requires auth)
  createMeasurement: async (data, token) => {
    const response = await api.post('/health-data/receive-measurement', data);
    return response.data;
  },

  // Get statistics
  getStats: async () => {
    const response = await api.get('/health-data/stats');
    return response.data;
  },

  // Send report via email (optional body: { email } for kiosk "enter email" flow)
  sendReportEmail: async (id, body = null) => {
    const response = await api.post(`/health-data/send-report-email/${id}`, body || {});
    return response.data;
  },

  // Get AI analysis (full JSON, structured)
  analyzeReport: async (id) => {
    const response = await api.get(`/health-data/analyze/${id}`);
    return response.data;
  },

  /**
   * Stream AI analysis as plain text (SSE). Returns the fetch Response so caller can read the stream.
   * Use with: response.body.getReader(), then decode and parse "data: {...}\n\n" lines.
   */
  getAnalyzeReportStreamUrl: (id) => {
    const base = api.defaults.baseURL || '';
    const token = localStorage.getItem('auth_token');
    const url = `${base}/health-data/analyze/${id}/stream`;
    return { url, token };
  },

  // Attribute measurement to a customer (staff/admin)
  attributeMeasurement: async (id, body) => {
    const response = await api.patch(`/health-data/receive-measurement/${id}`, body);
    return response.data;
  },
};

// Customer API
export const customerApi = {
  getCustomers: async (skip = 0, limit = 100) => {
    const response = await api.get('/customers/', { params: { skip, limit } });
    return response.data;
  },
  getCustomer: async (id) => {
    const response = await api.get(`/customers/${id}`);
    return response.data;
  },
  createCustomer: async (formData) => {
    const response = await api.post('/customers/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

// Device API
export const deviceApi = {
  getDevices: async () => {
    const response = await api.get('/devices/');
    return response.data;
  },
  createDevice: async (data) => {
    const response = await api.post('/devices/', data);
    return response.data;
  },
  /** Set multiple owners for a device. Pass empty array for public (no owners). */
  setDeviceOwners: async (deviceId, ownerIds) => {
    const response = await api.put(`/devices/${deviceId}/owners`, { owner_ids: ownerIds || [] });
    return response.data;
  },
  /** Owner dashboard: per-machine last report + counts (admin = all devices). */
  getMyMachinesStatus: async () => {
    const response = await api.get('/devices/my-machines-status', { params: { _: Date.now() } });
    return response.data;
  },
};

// Admin API
export const adminApi = {
  // Users – create (e.g. machine owner) by email
  createUser: async (email, role = 'customer', sendPin = true) => {
    const response = await api.post('/admin/users', { email, role, send_pin: sendPin });
    return response.data;
  },

  // Measurements
  getAllMeasurements: async (page = 1, pageSize = 20, patientId = null) => {
    const params = { page, page_size: pageSize };
    if (patientId) params.patient_id = patientId;
    const response = await api.get('/admin/measurements', { params });
    return response.data;
  },

  getMeasurement: async (id) => {
    const response = await api.get(`/admin/measurements/${id}`);
    return response.data;
  },

  updateMeasurement: async (id, data) => {
    const response = await api.put(`/admin/measurements/${id}`, data);
    return response.data;
  },

  deleteMeasurement: async (id) => {
    const response = await api.delete(`/admin/measurements/${id}`);
    return response.data;
  },

  // Users
  getAllUsers: async () => {
    const response = await api.get('/admin/users');
    return response.data;
  },

  getUser: async (id) => {
    const response = await api.get(`/admin/users/${id}`);
    return response.data;
  },

  updateUser: async (id, data) => {
    const response = await api.put(`/admin/users/${id}`, data);
    return response.data;
  },

  deleteUser: async (id) => {
    const response = await api.delete(`/admin/users/${id}`);
    return response.data;
  },

  promoteToAdmin: async (id) => {
    const response = await api.post(`/admin/users/${id}/make-admin`);
    return response.data;
  },
};

export default api;
