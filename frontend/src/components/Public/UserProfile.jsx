import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const PAGE_SIZE = 20;

const UserProfile = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const [user, setUser] = useState(null);
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mediaLoading, setMediaLoading] = useState(true);
  const [mediaPage, setMediaPage] = useState(1);
  const [hasMoreMedia, setHasMoreMedia] = useState(true);
  const [loadingMoreMedia, setLoadingMoreMedia] = useState(false);
  const sentinelRef = useRef(null);
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = useCallback(async (pageNum, append = false) => {
    const params = new URLSearchParams();
    params.append('user_id', id);
    params.append('page', pageNum);
    params.append('page_size', PAGE_SIZE);

    try {
      const res = await fetch(`${API_URL}/api/auth/media/public/?${params}`);
      if (!res.ok) {
        logger.warn('[UserProfile] Media fetch failed with status:', res.status);
        if (!append) setMedia([]);
        setHasMoreMedia(false);
        return;
      }
      const data = await res.json();
      const newMedia = Array.isArray(data) ? data : (data.results || []);
      if (append) {
        setMedia(prev => [...prev, ...newMedia]);
      } else {
        setMedia(newMedia);
      }
      setHasMoreMedia(newMedia.length === PAGE_SIZE);
    } catch (err) {
      logger.warn('[UserProfile] Media fetch error:', err);
      if (!append) setMedia([]);
      setHasMoreMedia(false);
    } finally {
      setMediaLoading(false);
      setLoadingMoreMedia(false);
    }
  }, [id, API_URL]);

  useEffect(() => {
    const fetchUserData = async () => {
      setLoading(true);
      setError(null);
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
      } finally {
        setLoading(false);
      }
    };
    fetchUserData();
  }, [id, API_URL]);

  useEffect(() => {
    setMediaPage(1);
    setHasMoreMedia(true);
    setMediaLoading(true);
    setMedia([]);
    fetchMedia(1, false);
  }, [id, fetchMedia]);

  useEffect(() => {
    if (!hasMoreMedia || loadingMoreMedia) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMoreMedia && !loadingMoreMedia) {
          setLoadingMoreMedia(true);
          const nextPage = mediaPage + 1;
          setMediaPage(nextPage);
          fetchMedia(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );
    const currentSentinel = sentinelRef.current;
    if (currentSentinel) observer.observe(currentSentinel);
    return () => {
      if (currentSentinel) observer.unobserve(currentSentinel);
    };
  }, [hasMoreMedia, loadingMoreMedia, mediaPage, fetchMedia]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

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
              <Link to={`/media/${item.id}`} state={{ media: item }} className="block">
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
                  <p className="text-gray-500 text-xs mt-2">
                    📅 {new Date(item.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              </Link>
            </div>
          ))}
          {hasMoreMedia && (
            <div ref={sentinelRef} className="col-span-full flex justify-center py-4">
              {loadingMoreMedia ? (
                <span className="text-gray-500">{t('loading_more')}</span>
              ) : (
                <span className="text-gray-400">&#8203;</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UserProfile;
