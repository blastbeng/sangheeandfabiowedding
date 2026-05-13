import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const UserProfile = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const [user, setUser] = useState(null);
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mediaLoading, setMediaLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchUserData = async () => {
      setLoading(true);
      setError(null);
      setMediaLoading(true);

      try {
        const userRes = await fetch(`${API_URL}/api/auth/users/public/${id}/`);
        if (userRes.status === 404) {
          setError('not_found');
          setLoading(false);
          return;
        }
        if (!userRes.ok) {
          setError(`http_error:${userRes.status}`);
          setLoading(false);
          return;
        }
        const userData = await userRes.json();
        setUser(userData);
      } catch (err) {
        logger.error('[UserProfile] Failed to fetch user data:', err);
        setError('network_error');
        setLoading(false);
        return;
      }

      try {
        const mediaRes = await fetch(`${API_URL}/api/auth/media/public/?user_id=${id}`);
        if (mediaRes.ok) {
          const mediaData = await mediaRes.json();
          setMedia(mediaData);
        } else {
          logger.warn('[UserProfile] Media fetch failed with status:', mediaRes.status);
        }
      } catch (err) {
        logger.warn('[UserProfile] Media fetch error:', err);
      } finally {
        setMediaLoading(false);
        setLoading(false);
      }
    };

    fetchUserData();
  }, [id, API_URL]);

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600 text-lg">{t('loading_profile')}</p>
      </div>
    );
  }

  if (error) {
    const errorMessage =
      error === 'not_found'
        ? t('user_not_found')
        : error === 'network_error'
          ? t('network_error', 'Network error. Please check your connection and try again.')
          : t('error_loading_profile');

    return (
      <div className="text-center py-20 wedding-card">
        <span className="text-6xl floating-heart inline-block">🌸</span>
        <p className="mt-4 text-red-500 text-lg">{errorMessage}</p>
        <Link to="/users" className="wedding-btn inline-block mt-4">{t('back_to_guests')}</Link>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="text-center py-20 wedding-card">
        <span className="text-6xl floating-heart inline-block">🌸</span>
        <p className="mt-4 text-gray-600 text-lg">{t('user_not_found')}</p>
        <Link to="/users" className="wedding-btn inline-block mt-4">{t('back_to_guests')}</Link>
      </div>
    );
  }

  const displayName = user.first_name && user.last_name
    ? `${user.first_name} ${user.last_name}`
    : user.username;

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="wedding-card p-8 text-center mb-8">
        <img
          src={user.profile_picture_url || `${API_URL}/media/profile_pics/default.png`}
          alt={displayName}
          className="w-28 h-28 rounded-full object-cover border-4 border-pink-200 mx-auto mb-4"
          onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
        />
        <h2 className="text-3xl wedding-title mb-2">{displayName}</h2>
        <p className="text-gray-500 text-sm">@{user.username}</p>
        <Link to="/users" className="text-pink-600 hover:text-pink-800 underline text-sm mt-2 inline-block">
          ← {t('back_to_guests')}
        </Link>
      </div>

      <div className="text-center mb-6">
        <h3 className="text-2xl wedding-title mb-2">{t('guest_uploads')}</h3>
        <p className="text-gray-600 italic">{t('guest_uploads_subtitle')}</p>
      </div>

      {mediaLoading ? (
        <div className="text-center py-10">
          <p className="text-gray-600">{t('loading', 'Loading...')}</p>
        </div>
      ) : media.length === 0 ? (
        <div className="text-center py-10 wedding-card">
          <span className="text-6xl floating-heart inline-block">📸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_uploads_from_guest')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {media.map((item) => (
            <div key={item.id} className="gallery-item bg-white shadow-lg">
              <div className="relative">
                {item.media_type === 'video' ? (
                  <video
                    src={`${API_URL}${item.file_url}`}
                    className="w-full h-48 object-cover"
                    controls
                  />
                ) : (
                  <img
                    src={`${API_URL}${item.file_url}`}
                    alt={item.caption || t('beautiful_moment')}
                    className="w-full h-48 object-cover"
                  />
                )}
              </div>
              <div className="p-4">
                <p className="text-gray-700 text-sm mb-2 line-clamp-2">
                  {item.caption || t('beautiful_moment')}
                </p>
                {item.face_tags && item.face_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.face_tags.map(tag => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-0.5 rounded-full bg-pink-50 text-pink-700 border border-pink-200"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-gray-500 text-xs mt-2">
                  📅 {new Date(item.uploaded_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UserProfile;
