import logger from './logger';

const API_URL = import.meta.env.VITE_API_URL;

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const authFetch = async (url, options = {}) => {
  const accessToken = localStorage.getItem('accessToken');
  
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${accessToken}`,
  };
  
  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      // No refresh token, force logout
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('isAdmin');
      window.location.href = '/login';
      throw new Error('No refresh token');
    }

    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${API_URL}/api/auth/token/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: refreshToken }),
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          localStorage.setItem('accessToken', data.access);
          // Retry original request with new token
          const newHeaders = {
            ...options.headers,
            'Authorization': `Bearer ${data.access}`,
          };
          if (options.body instanceof FormData) {
            delete newHeaders['Content-Type'];
          }
          response = await fetch(url, { ...options, headers: newHeaders });
          processQueue(null, data.access);
        } else {
          // Refresh failed, clear auth and redirect
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('isAdmin');
          processQueue(new Error('Refresh failed'));
          window.location.href = '/login';
          throw new Error('Token refresh failed');
        }
      } catch (error) {
        processQueue(error);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('isAdmin');
        window.location.href = '/login';
        throw error;
      } finally {
        isRefreshing = false;
      }
    } else {
      // Another request is already refreshing, queue this one
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(token => {
        const newHeaders = {
          ...options.headers,
          'Authorization': `Bearer ${token}`,
        };
        if (options.body instanceof FormData) {
          delete newHeaders['Content-Type'];
        }
        return fetch(url, { ...options, headers: newHeaders });
      });
    }
  }

  return response;
};

export default authFetch;
