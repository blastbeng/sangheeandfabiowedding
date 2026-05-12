import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const Profile = ({ setIsAuthenticated, setIsAdmin }) => {
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    first_name: '',
    last_name: '',
    email: ''
  });
  const [profilePicture, setProfilePicture] = useState(null);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    new_password_confirm: ''
  });
  const [hasPassword, setHasPassword] = useState(false);
  const [isDefaultAdmin, setIsDefaultAdmin] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await authFetch(`${API_URL}/api/auth/profile/`);
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setHasPassword(data.has_password);
          setIsDefaultAdmin(data.is_default_admin || false);
          setFormData({
            username: data.username || '',
            first_name: data.first_name || '',
            last_name: data.last_name || '',
            email: data.email || ''
          });
        } else {
          setError(t('profile_load_error'));
        }
      } catch (err) {
        logger.error('[Profile] Error loading profile:', err);
        setError(t('profile_load_generic_error'));
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [t, navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handlePasswordChange = (e) => {
    setPasswordData({ ...passwordData, [e.target.name]: e.target.value });
  };

  const handleProfilePictureChange = (e) => {
    if (e.target.files.length > 0) {
      setProfilePicture(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const data = new FormData();
    data.append('username', formData.username);
    data.append('first_name', formData.first_name);
    data.append('last_name', formData.last_name);
    data.append('email', formData.email);
    if (profilePicture) {
      data.append('profile_picture', profilePicture);
    }

    try {
      const res = await authFetch(`${API_URL}/api/auth/profile/`, {
        method: 'PUT',
        body: data
      });

      if (res.ok) {
        setSuccess(t('profile_update_success'));
        setProfilePicture(null);
      } else {
        const result = await res.json();
        setError(Object.values(result)[0] || t('profile_update_error'));
      }
    } catch (err) {
      logger.error('[Profile] Profile update error:', err);
      setError(t('profile_update_generic_error'));
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (passwordData.new_password !== passwordData.new_password_confirm) {
      setError(t('password_mismatch'));
      return;
    }

    const payload = {
      password: passwordData.new_password,
      password_confirm: passwordData.new_password_confirm,
    };
    if (hasPassword) {
      payload.current_password = passwordData.current_password;
    }

    try {
      const res = await authFetch(`${API_URL}/api/auth/profile/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setSuccess(t('password_update_success'));
        setPasswordData({ current_password: '', new_password: '', new_password_confirm: '' });
        // After setting a password, the user now has one – update the flag
        setHasPassword(true);
      } else {
        const data = await res.json();
        setError(data.detail || t('password_update_error'));
      }
    } catch (err) {
      logger.error('[Profile] Password update error:', err);
      setError(t('password_update_generic_error'));
    }
  };

  const handleDeleteAccount = () => {
    setShowDeleteModal(true);
  };

  const confirmDeleteAccount = async () => {
    setShowDeleteModal(false);
    try {
      const res = await authFetch(`${API_URL}/api/auth/profile/`, {
        method: 'DELETE'
      });
      if (res.ok || res.status === 204) {
        // Clear auth state and redirect to home
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('isAdmin');
        setIsAuthenticated(false);
        setIsAdmin(false);
        navigate('/', { replace: true });
      } else {
        const data = await res.json();
        setError(data.error || t('delete_account_error'));
      }
    } catch (err) {
      logger.error('[Profile] Delete account error:', err);
      setError(t('delete_account_error'));
    }
  };

  if (loading) {
    return <div className="text-center py-8">{t('Loading...')}</div>;
  }

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <div className="wedding-card p-8 text-center">
          <p className="text-red-600 mb-4">💔 {error || t('profile_load_generic_error')}</p>
          <button onClick={() => navigate('/login')} className="wedding-btn">
            {t('Sign In')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">👤 {t('Your Special Profile')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">
          {t('profile_subtitle')}
        </p>

        {error && (
          <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4">
            💔 {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">
            ✅ {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mb-8">
          <h3 className="text-xl font-bold mb-4 text-pink-600">📝 {t('About You')}</h3>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('Username')}</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="wedding-input w-full"
            />
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">{t('First Name')}</label>
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                className="wedding-input w-full"
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">{t('Last Name')}</label>
              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                className="wedding-input w-full"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('Email')}</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="wedding-input w-full"
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">🖼️ {t('Profile Picture')}</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleProfilePictureChange}
              className="wedding-input w-full"
            />
            {user.profile_picture_url && (
              <img src={`${API_URL}${user.profile_picture_url}`} alt={t('Current')} className="w-20 h-20 object-cover rounded-full mt-2 border-2 border-pink-200" />
            )}
          </div>
          <button type="submit" className="wedding-btn">
            💾 {t('Save Your Changes')}
          </button>
        </form>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <h3 className="text-xl font-bold mb-4 text-pink-600">🔐 {t('Keep Your Account Safe')}</h3>
        <form onSubmit={handlePasswordSubmit} className="mb-8">
          {hasPassword && (
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                🔐 {t('Current Password')}
              </label>
              <input
                type="password"
                name="current_password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                className="wedding-input w-full"
                placeholder="••••••••"
              />
            </div>
          )}
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('New Password')}</label>
            <input
              type="password"
              name="new_password"
              value={passwordData.new_password}
              onChange={handlePasswordChange}
              className="wedding-input w-full"
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('Confirm New Password')}</label>
            <input
              type="password"
              name="new_password_confirm"
              value={passwordData.new_password_confirm}
              onChange={handlePasswordChange}
              className="wedding-input w-full"
            />
          </div>
          <button type="submit" className="wedding-btn">
            🔑 {t('Update Password')}
          </button>
        </form>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <div className="mt-8">
          <h3 className="text-xl font-bold mb-4 text-pink-600">🌍 {t('Your Language')}</h3>
          <select
            value={i18n.language}
            onChange={(e) => {
              i18n.changeLanguage(e.target.value);
              localStorage.setItem('language', e.target.value);
            }}
            className="wedding-input w-full"
          >
            <option value="it">🇮🇹 {t('Italiano')}</option>
            <option value="ko">🇰🇷 {t('한국어')}</option>
            <option value="en">🇬🇧 {t('English')}</option>
          </select>
        </div>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <div className="mt-8 text-center">
          <button
            onClick={handleDeleteAccount}
            disabled={isDefaultAdmin}
            title={isDefaultAdmin ? t('Cannot delete default admin account') : ''}
            className={`bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-6 rounded-full transition shadow-md ${isDefaultAdmin ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            🗑️ {t('delete_account')}
          </button>
        </div>

        {/* Delete Account Confirmation Modal */}
        {showDeleteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 border-2 border-pink-200">
              <div className="text-center">
                <span className="text-5xl">⚠️</span>
                <h3 className="text-2xl font-bold text-pink-600 mt-4">{t('delete_account')}</h3>
                <p className="text-gray-700 mt-4 text-sm md:text-base">
                  {t('delete_account_confirm')}
                </p>
                <div className="flex gap-3 mt-6 justify-center">
                  <button
                    onClick={() => setShowDeleteModal(false)}
                    className="px-6 py-2 border-2 border-gray-300 rounded-full text-gray-600 hover:bg-gray-100 transition"
                  >
                    {t('admin_cancel')}
                  </button>
                  <button
                    onClick={confirmDeleteAccount}
                    className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white font-bold rounded-full transition shadow-md"
                  >
                    {t('confirm_delete_account')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
