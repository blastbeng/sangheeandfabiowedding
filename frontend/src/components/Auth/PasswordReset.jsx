import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const PasswordReset = () => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const { uidb64, token } = useParams();

  const isResetConfirm = uidb64 && token;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (isResetConfirm) {
        if (newPassword !== confirmPassword) {
          setError("Passwords don't match");
          return;
        }
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/password-reset-confirm/${uidb64}/${token}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: newPassword })
        });
        const data = await response.json();
        if (response.ok) {
          setSuccess(data.message);
          setTimeout(() => navigate('/login'), 2000);
        } else {
          setError(data.error);
        }
      } else {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/password-reset/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await response.json();
        if (response.ok) {
          setSuccess(data.message);
          if (data.debug_reset_url) {
            console.log('Debug reset URL:', data.debug_reset_url);
          }
        } else {
          setError(data.error);
        }
      }
    } catch (err) {
      setError(t('An error occurred'));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="wedding-card p-10 w-full max-w-md ribbon">
        <h2 className="text-4xl wedding-title text-center mb-2">
          {isResetConfirm ? t('Reset Password') : t('Forgot Password?')}
        </h2>
        <p className="text-center text-gray-600 mb-6 italic">
          {isResetConfirm 
            ? t('Enter your new password below') 
            : t('Enter your email and we will send you a reset link')}
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
          {!isResetConfirm ? (
            <div className="mb-6">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                📧 {t('Email')}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="wedding-input w-full"
                placeholder="your@email.com"
                required
              />
            </div>
          ) : (
            <>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  🔐 {t('New Password')}
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="wedding-input w-full"
                  placeholder="••••••••"
                  required
                />
              </div>
              <div className="mb-6">
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  🔐 {t('Confirm New Password')}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="wedding-input w-full"
                  placeholder="••••••••"
                  required
                />
              </div>
            </>
          )}
          <button type="submit" className="wedding-btn w-full mb-4">
            {isResetConfirm ? t('Reset Password') : t('Send Reset Link')}
          </button>
        </form>

        <div className="mt-4 text-center">
          <Link to="/login" className="text-wedding-azure hover:text-wedding-navy font-bold underline">
            ← {t('Back to Login')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default PasswordReset;
