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

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="wedding-card p-10 w-full max-w-md">
        <h2 className="text-4xl wedding-title text-center mb-2">Join Our Celebration!</h2>
        <p className="text-center text-gray-600 mb-6 italic">Create an account to share your precious moments 🌸</p>

        {error && <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4 text-center">💔 {error}</div>}
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4 text-center">✅ {success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">👤 Username</label>
            <input type="text" name="username" value={formData.username} onChange={handleChange} className="wedding-input w-full" placeholder="Choose a username" required />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">📧 Email</label>
            <input type="email" name="email" value={formData.email} onChange={handleChange} className="wedding-input w-full" placeholder="your@email.com" required />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">🔐 Password</label>
            <input type="password" name="password" value={formData.password} onChange={handleChange} className="wedding-input w-full" placeholder="••••••••" required />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">🔐 Confirm Password</label>
            <input type="password" name="password_confirm" value={formData.password_confirm} onChange={handleChange} className="wedding-input w-full" placeholder="••••••••" required />
          </div>
          <button type="submit" className="wedding-btn w-full mb-4">✨ Create Account</button>
        </form>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <div className="mt-4 text-center">
          <p className="text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="text-pink-600 hover:text-pink-800 font-bold underline">Sign In Here</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
