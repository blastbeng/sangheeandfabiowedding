import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const UserList = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);

    fetch(`${API_URL}/api/auth/users/public/?${params}`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        setUsers(data);
        setLoading(false);
      })
      .catch(err => {
        logger.error('[UserList] Failed to fetch users:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [search, API_URL]);

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600 text-lg">{t('loading_guests')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20 wedding-card">
        <span className="text-6xl floating-heart inline-block">🌸</span>
        <p className="mt-4 text-red-500 text-lg">{t('error_loading_guests', 'Failed to load guests. Please try again later.')}</p>
        <button
          onClick={() => window.location.reload()}
          className="wedding-btn inline-block mt-4"
        >
          {t('retry', 'Retry')}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="text-center mb-8">
        <h2 className="text-4xl wedding-title mb-2">{t('guests_title')}</h2>
        <p className="text-gray-600 italic">{t('guests_subtitle')}</p>
      </div>

      <div className="mb-6 flex justify-center">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="wedding-input w-full max-w-md"
          placeholder={t('search_guests_placeholder')}
        />
      </div>

      {users.length === 0 ? (
        <div className="text-center py-20 wedding-card">
          <span className="text-6xl floating-heart inline-block">🌸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_guests_yet')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
          {users.map((user) => (
            <Link
              key={user.id}
              to={`/user/${user.id}`}
              className="wedding-card p-4 flex flex-col items-center hover:shadow-xl transition-shadow"
            >
              <img
                src={user.profile_picture_url || `${API_URL}/media/profile_pics/default.png`}
                alt={user.username}
                className="w-20 h-20 rounded-full object-cover border-2 border-pink-200 mb-3"
                onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
              />
              <span className="text-gray-700 font-medium text-center text-sm">
                {user.first_name || user.last_name
                  ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                  : user.username}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default UserList;
