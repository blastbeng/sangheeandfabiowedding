import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useTranslation } from 'react-i18next';

const Login = ({ setIsAuthenticated, setIsAdmin }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem('isAdmin', data.user.is_staff);
        if (setIsAuthenticated) setIsAuthenticated(true);
        if (setIsAdmin) setIsAdmin(data.user.is_staff);
        navigate('/gallery');
      } else {
        setError(data.detail || t('Login failed'));
      }
    } catch (err) {
      setError(t('An error occurred during login'));
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/social/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'google',
          access_token: credentialResponse.credential
        })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem('isAdmin', data.user.is_staff);
        if (setIsAuthenticated) setIsAuthenticated(true);
        if (setIsAdmin) setIsAdmin(data.user.is_staff);
        navigate('/gallery');
      } else {
        setError(data.error || t('Google login failed'));
      }
    } catch (err) {
      setError(t('An error occurred during Google login'));
    }
  };

  const handleGoogleError = () => {
    setError(t('Google login failed'));
  };

  const handleFacebookLogin = async () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/social/facebook/`;
  };

  const handleInstagramLogin = async () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/social/instagram/`;
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="wedding-card p-10 w-full max-w-md ribbon">
        <h2 className="text-4xl wedding-title text-center mb-2">{t('Welcome Back!')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">
          We've missed you! Sign in to continue your love story with us 🌹
        </p>
        {error && (
          <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4 text-center">
            💔 {error}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
              👤 {t('Username')}
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder="yourusername"
              required
            />
          </div>
          <div className="mb-6">
            <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
              🔐 {t('Password')}
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" className="wedding-btn w-full mb-4">
            💝 {t('Sign In')}
          </button>
        </form>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <div className="mt-4">
          <p className="text-gray-600 text-center mb-3">{t('Or login with')}</p>
          <div className="flex gap-3 justify-center">
            {/* Google */}
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              text="signin_with"
              theme="filled_blue"
              size="large"
              width="200"
            />
            {/* Facebook */}
            <button
              onClick={handleFacebookLogin}
              className="wedding-btn bg-blue-600 hover:bg-blue-700 px-4 py-2 text-sm"
              style={{ background: '#1877F2' }}
            >
              📘 Facebook
            </button>
            {/* Instagram */}
            <button
              onClick={handleInstagramLogin}
              className="wedding-btn px-4 py-2 text-sm"
              style={{ background: 'linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)' }}
            >
              📷 Instagram
            </button>
          </div>
        </div>

        <div className="mt-4 text-center">
          <p className="text-gray-600">
            🌟 {t("Don't have an account?")}{" "}
            <Link to="/register" className="text-pink-600 hover:text-pink-800 font-bold underline">
              {t('Join Us')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
