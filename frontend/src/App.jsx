import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import VerifyEmail from './components/Auth/VerifyEmail';
import SocialCallback from './components/Auth/SocialCallback';
import PendingApproval from './components/Auth/PendingApproval';
import RegistrationSuccess from './components/Auth/RegistrationSuccess';
import Profile from './components/User/Profile';
import Upload from './components/User/Upload';
import MyUploads from './components/User/MyUploads';
import Gallery from './components/Public/Gallery';
import MediaView from './components/Public/MediaView';
import UserList from './components/Public/UserList';
import UserProfile from './components/Public/UserProfile';
import AdminModeration from './components/Admin/Moderation';
import AdminDashboard from './components/Admin/AdminDashboard';
import UserManagement from './components/Admin/UserManagement';
import Settings from './components/Admin/Settings';
import Home from './components/Public/Home';
import Events from './components/Public/Events';
import LanguageSwitcher from './components/Common/LanguageSwitcher';
import CookieConsent from './components/Common/CookieConsent';
import PasswordReset from './components/Auth/PasswordReset';
import { ErrorBoundary } from './main';
import logger from './utils/logger';

// Protected Route Component
const ProtectedRoute = ({ children, isAdminOnly = false, isAuthenticated, isAdmin }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (isAdminOnly && !isAdmin) {
    return <Navigate to="/" replace />;
  }
  return children;
};

const API_URL = import.meta.env.VITE_API_URL;
logger.info('[App] Initializing with API URL:', API_URL);

function App() {
  const { t, i18n } = useTranslation();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const isPendingApproval = location.pathname === '/pending-approval';

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const adminFlag = localStorage.getItem('isAdmin');
    logger.info('[App] Auth state - Token present:', !!token, 'Is Admin:', adminFlag);
    
    if (token) {
      setIsAuthenticated(true);
      setIsAdmin(adminFlag === 'true');
    }
    setLoading(false);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('isAdmin');
    setIsAuthenticated(false);
    setIsAdmin(false);
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  return (
    <Router>
      <div className="min-h-screen bg-gray-100 flex flex-col">
        {!isPendingApproval && (
          <header className="wedding-header text-white p-4">
            <div className="max-w-6xl mx-auto flex flex-col items-center gap-3">
              {/* Line 1: Language Switcher */}
              <LanguageSwitcher />
              
              {/* Line 2: Navigation Links */}
              <nav className="flex flex-wrap gap-4 items-center justify-center">
                <Link to="/" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('Home')}</Link>
                <Link to="/events" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">
                  {t('Event')}
                </Link>
                <Link to="/gallery" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('Gallery')}</Link>
                <Link to="/users" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('Guests')}</Link>
              </nav>
              
              {/* Line 3: Auth Buttons */}
              <div className="flex flex-wrap gap-3 items-center justify-center">
                {isAuthenticated ? (
                  <>
                    <Link to="/upload" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('Share')}</Link>
                    <Link to="/my-uploads" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('My Uploads')}</Link>
                    <Link to="/profile" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">{t('Profile')}</Link>
                    {isAdmin && (
                      <Link to="/admin" className="hover:text-yellow-200 transition font-medium text-sm md:text-base whitespace-nowrap">⭐ Admin</Link>
                    )}
                    <button onClick={handleLogout} className="border-2 border-white/80 text-white rounded-full px-3 md:px-4 py-2 text-xs md:text-sm font-semibold hover:bg-white/20 transition-all whitespace-nowrap">
                      {t('Logout')}
                    </button>
                  </>
                ) : (
                  <>
                    <Link to="/login" className="border-2 border-white/80 text-white rounded-full px-3 md:px-4 py-2 text-xs md:text-sm font-semibold hover:bg-white/20 transition-all whitespace-nowrap">{t('Sign In')}</Link>
                    <Link to="/register" className="border-2 border-white/80 text-white rounded-full px-3 md:px-4 py-2 text-xs md:text-sm font-semibold hover:bg-white/20 transition-all whitespace-nowrap">{t('Join Us')}</Link>
                  </>
                )}
              </div>
            </div>
          </header>
        )}

        <main className={`flex-grow ${!isPendingApproval ? 'p-4' : ''}`}>
          <div className={!isPendingApproval ? 'max-w-6xl mx-auto' : ''}>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Home isAuthenticated={isAuthenticated} />} />
                <Route path="/events" element={<Events />} />
                <Route path="/gallery" element={<Gallery />} />
                <Route path="/media/:id" element={<MediaView />} />
                <Route path="/users" element={<UserList />} />
                <Route path="/user/:id" element={<UserProfile />} />
                <Route 
                  path="/verify-email" 
                  element={
                    <VerifyEmail setIsAuthenticated={setIsAuthenticated} setIsAdmin={setIsAdmin} />
                  } 
                />
                <Route 
                  path="/social-callback" 
                  element={
                    <SocialCallback setIsAuthenticated={setIsAuthenticated} setIsAdmin={setIsAdmin} />
                  } 
                />
                <Route path="/pending-approval" element={<PendingApproval />} />
                <Route path="/registration-success" element={<RegistrationSuccess />} />
                <Route 
                  path="/login" 
                  element={
                    isAuthenticated 
                      ? <Navigate to="/" replace /> 
                      : <Login setIsAuthenticated={setIsAuthenticated} setIsAdmin={setIsAdmin} />
                  } 
                />
                <Route 
                  path="/register" 
                  element={
                    isAuthenticated 
                      ? <Navigate to="/" replace /> 
                      : <Register setIsAuthenticated={setIsAuthenticated} setIsAdmin={setIsAdmin} />
                  } 
                />
                <Route 
                  path="/password-reset" 
                  element={<PasswordReset />} 
                />
                <Route 
                  path="/password-reset-confirm/:uidb64/:token" 
                  element={<PasswordReset />} 
                />
                <Route 
                  path="/profile" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated}>
                      <Profile setIsAuthenticated={setIsAuthenticated} setIsAdmin={setIsAdmin} />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/upload" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated}>
                      <Upload />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/my-uploads" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated}>
                      <MyUploads />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/admin" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated} isAdminOnly={true} isAdmin={isAdmin}>
                      <AdminDashboard />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/admin/users" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated} isAdminOnly={true} isAdmin={isAdmin}>
                      <UserManagement />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/admin/settings" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated} isAdminOnly={true} isAdmin={isAdmin}>
                      <Settings />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/admin/moderation" 
                  element={
                    <ProtectedRoute isAuthenticated={isAuthenticated} isAdminOnly={true} isAdmin={isAdmin}>
                      <AdminModeration />
                    </ProtectedRoute>
                  } 
                />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>

        <CookieConsent />

        {!isPendingApproval && (
          <footer className="bg-gradient-to-r from-wedding-navy via-wedding-azure to-wedding-navy text-white text-center p-6">
            <p className="text-2xl mb-2 text-white" style={{ fontFamily: "'Great Vibes', cursive", textShadow: '0 2px 4px rgba(0,0,0,0.3)' }}>🌸 {t('footer_crafted')} 🌸</p>
            <p className="text-sm opacity-80">
              {t('footer_thank_you')}
            </p>
            <p className="text-xs opacity-60 mt-2">
              © 2026 {t('footer_project')} - {t('footer_forever')}
            </p>
          </footer>
        )}
      </div>
    </Router>
  );
}

export default App;
