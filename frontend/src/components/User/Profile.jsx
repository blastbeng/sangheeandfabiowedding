import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const Profile = () => {
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    first_name: '',
    last_name: '',
    email: ''
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    new_password_confirm: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch(`${API_URL}/api/auth/profile/`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setFormData({
            username: data.username || '',
            first_name: data.first_name || '',
            last_name: data.last_name || '',
            email: data.email || ''
          });
        } else {
          setError('Failed to load profile');
        }
      } catch (err) {
        setError('An error occurred while loading profile');
      }
    };
    fetchProfile();
  }, []);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handlePasswordChange = (e) => {
    setPasswordData({
      ...passwordData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const res = await fetch(`${API_URL}/api/auth/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        setSuccess('Profile updated successfully');
      } else {
        const data = await res.json();
        setError(Object.values(data)[0] || 'Failed to update profile');
      }
    } catch (err) {
      setError('An error occurred while updating profile');
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (passwordData.new_password !== passwordData.new_password_confirm) {
      setError("New passwords don't match");
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/auth/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify({
          current_password: passwordData.current_password,
          password: passwordData.new_password
        })
      });

      if (res.ok) {
        setSuccess('Password updated successfully');
        setPasswordData({
          current_password: '',
          new_password: '',
          new_password_confirm: ''
        });
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to update password');
      }
    } catch (err) {
      setError('An error occurred while updating password');
    }
  };

  if (!user) return <div>Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">👤 {t('Your Special Profile')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">
          Tell us about yourself, lovely! 💕
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
          <button type="submit" className="wedding-btn">
            💾 {t('Save Your Changes')}
          </button>
        </form>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <h3 className="text-xl font-bold mb-4 text-pink-600">🔐 {t('Keep Your Account Safe')}</h3>
        <form onSubmit={handlePasswordSubmit} className="mb-8">
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('Current Password')}</label>
            <input
              type="password"
              name="current_password"
              value={passwordData.current_password}
              onChange={handlePasswordChange}
              className="wedding-input w-full"
            />
          </div>
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
      </div>
    </div>
  );
};

export default Profile;
