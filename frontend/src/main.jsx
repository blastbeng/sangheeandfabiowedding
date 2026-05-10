import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App.jsx'
import './i18n'
import './index.css'

if (import.meta.env.DEV) {
  console.log('[Main] App starting in development mode');
  console.log('[Main] Google Client ID configured:', !!import.meta.env.VITE_GOOGLE_CLIENT_ID);
  console.log('[Main] API URL:', import.meta.env.VITE_API_URL);
}

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    console.error('[ErrorBoundary] Caught error:', error);
    // Immediately redirect to /login – do not show fallback UI
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('isAdmin');
    window.location.href = '/login';
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Error info:', errorInfo);
  }

  render() {
    // If an error occurred, the redirect has already been triggered.
    // Return null to avoid flashing the fallback UI.
    if (this.state.hasError) {
      return null;
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
        <App />
      </GoogleOAuthProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
