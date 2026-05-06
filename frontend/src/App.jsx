import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Profile from './components/User/Profile';
import Upload from './components/User/Upload';
import MyUploads from './components/User/MyUploads';
import Gallery from './components/Public/Gallery';
import AdminModeration from './components/Admin/Moderation';
import AdminDashboard from './components/Admin/AdminDashboard';
import UserManagement from './components/Admin/UserManagement';
import Settings from './components/Admin/Settings';
import Home from './components/Public/Home';
import Events from './components/Public/Events';

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

function App() {
  const { t } = useTranslation();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const adminFlag = localStorage.getItem('isAdmin');
    
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
        <header className="wedding-header text-white p-4">
          <div className="max-w-6xl mx-auto flex justify-between items-center">
            <h1 className="text-3xl wedding-title">💕 Our Forever Begins 💕</h1>
            <nav className="flex gap-4 items-center">
              <a href="/" className="hover:text-yellow-200 transition font-medium">{t('Home')}</a>
              <a href="/events" className="hover:text-yellow-200 transition font-medium">📅 Events</a>
              <a href="/gallery" className="hover:text-yellow-200 transition font-medium">{t('Gallery')}</a>
              {isAuthenticated ? (
                <>
                  <a href="/upload" className="hover:text-yellow-200 transition font-medium">{t('Share')}</a>
                  <a href="/my-uploads" className="hover:text-yellow-200 transition font-medium">{t('My Uploads')}</a>
                  <a href="/profile" className="hover:text-yellow-200 transition font-medium">{t('Profile')}</a>
                  {isAdmin && (
                    <a href="/admin" className="hover:text-yellow-200 transition font-medium">⭐ Admin Panel</a>
                  )}
                  <button onClick={handleLogout} className="wedding-btn text-sm px-4 py-2">
                    {t('Logout')}
                  </button>
                </>
              ) : (
                <>
                  <a href="/login" className="wedding-btn text-sm px-4 py-2">{t('Sign In')}</a>
                  <a href="/register" className="wedding-btn text-sm px-4 py-2">{t('Join Us')}</a>
                </>
              )}
            </nav>
          </div>
        </header>

        <main className="flex-grow p-4">
          <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/events" element={<Events />} />
              <Route path="/gallery" element={<Gallery />} />
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
                    : <Register />
                } 
              />
              <Route 
                path="/profile" 
                element={
                  <ProtectedRoute isAuthenticated={isAuthenticated}>
                    <Profile />
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
          </div>
        </main>

        <footer className="bg-gradient-to-r from-pink-900 via-purple-900 to-pink-900 text-white text-center p-6">
          <p className="wedding-title text-2xl mb-2">🌸 Crafted with Endless Love 🌸</p>
          <p className="text-sm opacity-80">
            Thank you for being part of our beautiful journey together 💕
          </p>
          <p className="text-xs opacity-60 mt-2">
            &copy; 2024 Our Wedding Memory Project - Forever & Always
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
