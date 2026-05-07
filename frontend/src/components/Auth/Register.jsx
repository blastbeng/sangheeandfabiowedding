import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useTranslation } from 'react-i18next';

const Register = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.password_confirm) {
      setError("Passwords don't match");
      return;
    }
    try {
      const response = await fetch('http://localhost:8000/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        setSuccess('Account created successfully! 🎉');
        setTimeout(() => navigate('/gallery'), 2000);
      } else {
        setError(Object.values(data)[0] || 'Registration failed');
      }
    } catch (err) {
      setError('An error occurred during registration');
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await fetch('http://localhost:8000/api/auth/social/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'google', access_token: credentialResponse.credential })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        navigate('/gallery');
      } else {
        setError(data.error || 'Google registration failed');
      }
    } catch (err) {
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
              placeholder="Something special just for you"
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
              placeholder="your@happymail.com"
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
              placeholder="Make it strong & secret!"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              🔐 {t('Confirm New Password')}
            </label>
            <input
              type="password"
              name="password_confirm"
              value={formData.password_confirm}
              onChange={handleChange}
              className="wedding-input w-full"
              placeholder="Same as above, please!"
              required
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
            <div className="flex justify-center w-full">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                text="signup_with"
                theme="filled_blue"
                size="large"
                width="100%"
              />
            </div>
            {/* Facebook */}
            <button
              onClick={handleFacebookLogin}
              className="w-full py-3 px-4 rounded-xl font-semibold text-white transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
              style={{ background: '#1877F2' }}
            >
              <span className="text-lg">📘</span>
              <span>Facebook</span>
            </button>
            {/* Instagram */}
            <button
              onClick={handleInstagramLogin}
              className="w-full py-3 px-4 rounded-xl font-semibold text-white transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
              style={{ background: 'linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)' }}
            >
              <span className="text-lg">📷</span>
              <span>Instagram</span>
            </button>
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
