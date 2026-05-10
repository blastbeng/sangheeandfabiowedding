import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const VerifyEmail = () => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    const error = searchParams.get('error');
    const success = searchParams.get('success');

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

    if (token) {
      // The backend will redirect, but we can also call the API directly
      fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify-email/?token=${token}`)
        .then(res => res.json())
        .then(data => {
          if (data.message) {
            setStatus('success');
            setMessage(data.message);
          } else if (data.error) {
            setStatus('error');
            setMessage(data.error);
          }
        })
        .catch(() => {
          setStatus('error');
          setMessage(t('verify_network_error'));
        });
    } else {
      setStatus('error');
      setMessage(t('verify_no_token'));
    }
  }, [searchParams, t]);

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
            <Link to="/login" className="wedding-btn inline-block mt-6">{t('go_to_login')}</Link>
          </>
        )}
        {status === 'error' && (
          <>
            <span className="text-5xl inline-block">❌</span>
            <h2 className="text-2xl wedding-title mt-4">{t('verification_failed')}</h2>
            <p className="text-gray-600 mt-2">{message}</p>
            <Link to="/" className="wedding-btn inline-block mt-6">{t('back_to_home')}</Link>
          </>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
