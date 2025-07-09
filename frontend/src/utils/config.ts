// Frontend configuration utility
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '10000'),
  },
  app: {
    title: import.meta.env.VITE_APP_TITLE || 'Log Dawg Dashboard',
    version: import.meta.env.VITE_APP_VERSION || '1.0.0',
    debug: import.meta.env.VITE_DEBUG === 'true',
    logLevel: import.meta.env.VITE_LOG_LEVEL || 'INFO',
  },
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

// Configuration helper functions
export const getApiBaseUrl = () => config.api.baseUrl;
export const getAppTitle = () => config.app.title;
export const isDebugMode = () => config.app.debug;
export const getApiTimeout = () => config.api.timeout;
export const getAppVersion = () => config.app.version;
export const getLogLevel = () => config.app.logLevel;
