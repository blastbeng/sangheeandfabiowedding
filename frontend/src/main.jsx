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
    this.state = { hasError: false, error: null };
    this.redirectTimer = null;
  }

  static getDerivedStateFromError(error) {
    console.error('[ErrorBoundary] Caught error:', error);
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Error info:', errorInfo);
  }

  componentDidMount() {
    if (this.state.hasError) {
      this.redirectTimer = setTimeout(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('isAdmin');
        window.location.href = '/';
      }, 5000);
    }
  }

  componentWillUnmount() {
    if (this.redirectTimer) {
      clearTimeout(this.redirectTimer);
    }
  }

  render() {
    if (this.state.hasError) {
      const containerStyle = {
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fef2f2',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      };
      const boxStyle = {
        textAlign: 'center',
        padding: '2rem',
        maxWidth: '400px',
      };
      const headingStyle = {
        fontSize: '1.5rem',
        color: '#dc2626',
        marginBottom: '1rem',
      };
      const textStyle = {
        color: '#4b5563',
        marginBottom: '1.5rem',
      };
      const buttonStyle = {
        backgroundColor: '#dc2626',
        color: 'white',
        border: 'none',
        padding: '0.75rem 1.5rem',
        borderRadius: '0.375rem',
        cursor: 'pointer',
        fontSize: '1rem',
      };

      return (
        <div style={containerStyle}>
          <div style={boxStyle}>
            <h1 style={headingStyle}>Something went wrong</h1>
            <p style={textStyle}>
              You will be redirected to the home page in a few seconds.
            </p>
            <button
              style={buttonStyle}
              onClick={() => {
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
                localStorage.removeItem('isAdmin');
                window.location.href = '/';
              }}
            >
              Go to Home Now
            </button>
          </div>
        </div>
      );
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
