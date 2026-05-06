import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Profile from './components/User/Profile';
import Upload from './components/User/Upload';
import MyUploads from './components/User/MyUploads';
import Gallery from './components/Public/Gallery';
import AdminModeration from './components/Admin/Moderation';
import Home from './components/Public/Home';

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
        <header className="bg-blue-600 text-white p-4">
          <div className="max-w-6xl mx-auto flex justify-between items-center">
            <h1 className="text-2xl font-bold">Wedding Media</h1>
            <nav className="flex gap-4">
              <a href="/" className="hover:underline">Gallery</a>
              {isAuthenticated ? (
                <>
                  <a href="/upload" className="hover:underline">Upload</a>
                  <a href="/my-uploads" className="hover:underline">My Uploads</a>
                  <a href="/profile" className="hover:underline">Profile</a>
                  {isAdmin && (
                    <a href="/admin/moderation" className="hover:underline">Moderation</a>
                  )}
                  <button onClick={handleLogout} className="hover:underline">Logout</button>
                </>
              ) : (
                <>
                  <a href="/login" className="hover:underline">Login</a>
                  <a href="/register" className="hover:underline">Register</a>
                </>
              )}
            </nav>
          </div>
        </header>

        <main className="flex-grow p-4">
          <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Home />} />
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

        <footer className="bg-gray-800 text-white text-center p-4">
          <p>&copy; 2024 Wedding Media Project</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
