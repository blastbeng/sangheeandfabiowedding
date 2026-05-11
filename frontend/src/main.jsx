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
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex items-center justify-center p-4">
          <div className="wedding-card p-8 max-w-md w-full text-center">
            <span className="text-5xl inline-block">💔</span>
            <h2 className="text-2xl wedding-title mt-4">Oops! Something went wrong</h2>
            <p className="text-gray-600 mt-2">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="wedding-btn mt-6"
            >
              Refresh Page
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
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
)

export { ErrorBoundary };
