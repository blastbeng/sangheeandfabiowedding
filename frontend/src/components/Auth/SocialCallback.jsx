import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const SocialCallback = ({ setIsAuthenticated, setIsAdmin }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const access = searchParams.get('access');
    const refresh = searchParams.get('refresh');

    if (access && refresh) {
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      setIsAuthenticated(true);
      // Fetch user profile to check admin status
      fetch(`${import.meta.env.VITE_API_URL}/api/auth/profile/`, {
        headers: { 'Authorization': `Bearer ${access}` }
      })
        .then(res => res.json())
        .then(data => {
          if (data.is_staff) {
            localStorage.setItem('isAdmin', 'true');
            setIsAdmin(true);
          }
          navigate('/', { replace: true });
        })
        .catch(() => {
          navigate('/', { replace: true });
        });
    } else {
      navigate('/login?error=social_callback_failed', { replace: true });
    }
  }, [searchParams, navigate, setIsAuthenticated, setIsAdmin]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p>Completing login...</p>
    </div>
  );
};

export default SocialCallback;
