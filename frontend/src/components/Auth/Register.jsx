import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const Register = ({ setIsAuthenticated, setIsAdmin }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  });
  const [profilePicture, setProfilePicture] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [socialProviders, setSocialProviders] = useState({
    google: false,
    googleClientId: null,
    facebook: false,
    instagram: false
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/auth/social/status/`)
      .then(res => res.json())
      .then(data => setSocialProviders({
          google: data.google,
          googleClientId: data.google_client_id || null,
          facebook: data.facebook,
          instagram: data.instagram,
      }))
      .catch(err => logger.error('[Register] Failed to fetch social providers status:', err));
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Password match check
    if (formData.password !== formData.password_confirm) {
      setError(t('password_mismatch'));
      return;
    }

    // Password strength checks
    if (formData.password.length < 8) {
      setError(t('password_too_short'));
      return;
    }
    if (!/[a-z]/.test(formData.password)) {
      setError(t('password_requirements'));
      return;
    }
    if (!/[A-Z]/.test(formData.password)) {
      setError(t('password_requirements'));
      return;
    }
    if (!/[0-9]/.test(formData.password)) {
      setError(t('password_requirements'));
      return;
    }

    const data = new FormData();
    data.append('username', formData.username);
    data.append('email', formData.email);
    data.append('password', formData.password);
    data.append('password_confirm', formData.password_confirm);
    if (profilePicture) {
      data.append('profile_picture', profilePicture);
    }

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/register/`, {
        method: 'POST',
        body: data,
      });
      const result = await response.json();
      if (response.ok) {
        setSuccess(t('verify_success'));
      } else {
        // Handle specific known errors with translations
        if (result.email) {
          setError(t('email_already_exists'));
        } else if (result.username) {
          setError(t('username_already_taken'));
        } else {
          // Fallback: extract first error message
          const firstError = Object.values(result)[0];
          const message = Array.isArray(firstError) ? firstError[0] : firstError;
          setError(message || t('registration_failed'));
        }
      }
    } catch (err) {
      logger.error('[Register] Registration error:', err);
      setError(t('error_during_registration'));
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/social/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'google', access_token: credentialResponse.credential })
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
        setError(data.error || 'Google registration failed');
      }
    } catch (err) {
      logger.error('[Register] Google registration error:', err);
      setError('An error occurred during Google registration');
    }
  };

  const handleGoogleError = () => setError('Google registration failed');
  
  const handleFacebookLogin = async () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/social/facebook/`;
  };

  const handleInstagramLogin = async () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/social/instagram/`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="wedding-card p-10 w-full max-w-md ribbon">
        <h2 className="text-4xl wedding-title text-center mb-2">{t('Join Our Celebration!')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">
          Create your account and become part of our beautiful love story 🌸
        </p>

        {error && (
          <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4 text-center">
            💔 {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4 text-center">
            ✅ {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              👤 {t('Username')}
            </label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder={t('register_username_placeholder')}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              📧 {t('Email')}
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder={t('register_email_placeholder')}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              🔐 {t('Password')}
            </label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder={t('register_password_placeholder')}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              🔐 {t('Confirm New Password')}
            </label>
            <input
              type="password"
              name="password_confirm"
              value={formData.password_confirm}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder={t('register_password_confirm_placeholder')}
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              🖼️ {t('Profile Picture')} ({t('optional')})
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setProfilePicture(e.target.files[0])}
              className="wedding-input w-full"
            />
          </div>
          <button type="submit" className="wedding-btn w-full mb-4">
            ✨ {t('Create Account')}
          </button>
        </form>

        <div className="mt-6">
          <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
          <p className="text-gray-600 text-center mb-4 text-sm">{t('Or register with')}</p>
          <div className="flex flex-col gap-3 w-full">
            {/* Google */}
            {socialProviders.google && socialProviders.googleClientId && (
              <div className="h-10 w-full">
                <GoogleLogin
                  clientId={socialProviders.googleClientId}
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  text="signup_with"
                  theme="filled_blue"
                  size="large"
                  width="100%"
                />
              </div>
            )}
            {/* Facebook */}
            {socialProviders.facebook && (
              <button
                onClick={handleFacebookLogin}
                className="h-10 w-full px-4 rounded-xl font-semibold text-white text-sm transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                style={{ background: '#1877F2' }}
              >
                <span className="text-lg">📘</span>
                <span>Facebook</span>
              </button>
            )}
            {/* Instagram */}
            {socialProviders.instagram && (
              <button
                onClick={handleInstagramLogin}
                className="h-10 w-full px-4 rounded-xl font-semibold text-white text-sm transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                style={{ background: 'linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)' }}
              >
                <span className="text-lg">📷</span>
                <span>Instagram</span>
              </button>
            )}
          </div>
        </div>

        <div className="mt-4 text-center">
          <p className="text-gray-600">
            {t('Already have an account?')}{" "}
            <Link to="/login" className="text-pink-600 hover:text-pink-800 font-bold underline">
              {t('Sign In Here')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
