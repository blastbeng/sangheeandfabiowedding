// Reload the page if a chunk fails to load (prevents browser error page)
window.addEventListener('unhandledrejection', function(event) {
  if (event.reason && event.reason.message &&
      event.reason.message.includes('Failed to fetch dynamically imported module')) {
    console.warn('Chunk load failed, reloading...');
    window.location.reload();
  }
});

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

// Error Boundary Component – shows a loading spinner on error, then reloads
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
    // Prevent infinite reload loops – only reload once per session
    const alreadyReloaded = sessionStorage.getItem('error_reload');
    if (!alreadyReloaded) {
      sessionStorage.setItem('error_reload', '1');
      // Reload after a tiny delay so the spinner is painted
      setTimeout(() => window.location.reload(), 100);
    }
  }

  render() {
    if (this.state.hasError) {
      // Full-page loading spinner – identical to the initial loader
      return (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          background: '#fdf2f8', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 9999
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '3rem' }}>💕</div>
            <p style={{ color: '#ec4899', fontFamily: 'Georgia,serif', fontSize: '1.2rem' }}>
              Loading...
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const isGoogleValid = googleClientId && googleClientId.endsWith('.apps.googleusercontent.com');

const appContent = isGoogleValid ? (
  <GoogleOAuthProvider clientId={googleClientId}>
    <App />
  </GoogleOAuthProvider>
) : (
  <App />
);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {appContent}
  </React.StrictMode>,
)

export { ErrorBoundary };
