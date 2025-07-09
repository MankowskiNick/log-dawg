import axios from 'axios';
import { getApiBaseUrl, getApiTimeout } from '../utils/config';

// Create axios instance with configuration
const apiClient = axios.create({
  baseURL: `${getApiBaseUrl()}/api/v1`,
  timeout: getApiTimeout(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging in development
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (import.meta.env.DEV) {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const reportsApi = {
  getReports: () => apiClient.get('/reports'),
  getReport: (reportId: string) => apiClient.get(`/reports/${reportId}`),
  deleteReport: (reportId: string) => apiClient.delete(`/reports/${reportId}`),
  downloadMarkdown: (reportId: string) =>
    apiClient.post(`/reports/${reportId}/download/markdown`, {}, { responseType: 'blob' }),
};

export const systemApi = {
  getHealth: () => apiClient.get('/health'),
  getStats: () => apiClient.get('/stats'),
};

export default apiClient;
