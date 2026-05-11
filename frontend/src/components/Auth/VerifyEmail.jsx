import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const VerifyEmail = ({ setIsAuthenticated, setIsAdmin }) => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const access = searchParams.get('access');
    const refresh = searchParams.get('refresh');
    const error = searchParams.get('error');
    const success = searchParams.get('success');
    const statusParam = searchParams.get('status');

    // Handle pending approval status (email verified but admin hasn't activated yet)
    if (statusParam === 'pending_approval') {
      setStatus('success');
      setMessage(t('verify_pending_approval'));
      return;
    }

    // If tokens are present, log the user in automatically
    if (access && refresh) {
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      // Fetch user profile to determine admin status
      fetch(`${import.meta.env.VITE_API_URL}/api/auth/profile/`, {
        headers: { 'Authorization': `Bearer ${access}` }
      })
        .then(res => res.json())
        .then(data => {
          setIsAdmin(data.is_staff || false);
          localStorage.setItem('isAdmin', data.is_staff ? 'true' : 'false');
          setIsAuthenticated(true);
          navigate('/', { replace: true });
        })
        .catch(() => {
          // If profile fetch fails, still set authenticated and redirect
          setIsAuthenticated(true);
          navigate('/', { replace: true });
        });
      return;
    }

    // Handle error messages
    if (error) {
      setStatus('error');
      switch (error) {
        case 'missing_token': setMessage(t('verify_missing_token')); break;
        case 'expired': setMessage(t('verify_expired')); break;
        case 'invalid': setMessage(t('verify_invalid')); break;
        case 'user_not_found': setMessage(t('verify_user_not_found')); break;
        default: setMessage(t('verify_unknown_error'));
      }
      return;
    }

    if (success) {
      setStatus('success');
      const msgParam = searchParams.get('message');
      if (msgParam) {
        setMessage(decodeURIComponent(msgParam));
      } else if (success === 'already_verified') {
        setMessage(t('verify_already_verified'));
      } else if (success === 'verified') {
        setMessage(t('verify_success'));
      }
      return;
    }

    // Fallback: if no tokens and no error/success, show loading
    setStatus('loading');
  }, [searchParams, t, navigate, setIsAuthenticated, setIsAdmin]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="wedding-card p-8 max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <span className="text-5xl heart-decoration inline-block">💝</span>
            <p className="mt-4 text-gray-600">{t('verifying')}</p>
          </>
        )}
        {status === 'success' && (
          <>
            <span className="text-5xl inline-block">✅</span>
            <h2 className="text-2xl wedding-title mt-4">{t('email_verified')}</h2>
            <p className="text-gray-600 mt-2">{message}</p>
            <button onClick={() => navigate('/login')} className="wedding-btn inline-block mt-6">{t('go_to_login')}</button>
          </>
        )}
        {status === 'error' && (
          <>
            <span className="text-5xl inline-block">❌</span>
            <h2 className="text-2xl wedding-title mt-4">{t('verification_failed')}</h2>
            <p className="text-gray-600 mt-2">{message}</p>
            <button onClick={() => navigate('/')} className="wedding-btn inline-block mt-6">{t('back_to_home')}</button>
          </>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
