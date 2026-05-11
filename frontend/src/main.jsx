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

// Error Boundary Component – silently reloads on error to avoid flashing an error page
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
      window.location.reload();
    }
    // If already reloaded, do nothing – the error will be uncaught and the app may break,
    // but we avoid an infinite loop. The user will see a blank page.
  }

  render() {
    if (this.state.hasError) {
      // Render nothing while the reload is pending (or if already reloaded)
      return null;
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
