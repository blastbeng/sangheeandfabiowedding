import { useEffect, useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import logger from '../../utils/logger';

const PAGE_SIZE = 20;

const Gallery = () => {
  const { t, i18n } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [faceGroups, setFaceGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [failedMediaIds, setFailedMediaIds] = useState(new Set());
  const API_URL = import.meta.env.VITE_API_URL;

  const sentinelRef = useRef(null);

  // Filter out face groups that have no tags (empty groups)
  const activeFaceGroups = faceGroups.filter(g => g.face_count === undefined || g.face_count > 0);

  const fetchMedia = useCallback(async (pageNum, append = false) => {
    const params = new URLSearchParams();
    if (selectedUserId) params.append('user_id', selectedUserId);
    if (selectedGroupId) {
      params.append('face_group_id', selectedGroupId);
    }
    params.append('page', pageNum);
    params.append('page_size', PAGE_SIZE);

    try {
      const res = await fetch(`${API_URL}/api/auth/media/public/?${params}`);
      const data = await res.json();
      const newMedia = Array.isArray(data) ? data : (data.results || []);
      if (append) {
        setMedia(prev => [...prev, ...newMedia]);
      } else {
        setMedia(newMedia);
        setFailedMediaIds(new Set());
      }
      setHasMore(newMedia.length === PAGE_SIZE);
      setLoading(false);
      setLoadingMore(false);
    } catch (err) {
      logger.error('[Gallery] Failed to fetch media:', err);
      setLoading(false);
      setLoadingMore(false);
    }
  }, [selectedUserId, selectedGroupId, API_URL]);

  useEffect(() => {
    setPage(1);
    setHasMore(true);
    setLoading(true);
    fetchMedia(1, false);
  }, [selectedUserId, selectedGroupId, fetchMedia]);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/face-groups/`)
      .then(res => res.json())
      .then(data => setFaceGroups(data))
      .catch(err => logger.error('[Gallery] Failed to fetch face groups:', err));
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/users/public/`)
      .then(res => res.json())
      .then(data => setUsers(Array.isArray(data) ? data : []))
      .catch(err => logger.error('[Gallery] Failed to fetch users:', err));
  }, [API_URL]);

  useEffect(() => {
    if (!hasMore || loadingMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          setLoadingMore(true);
          const nextPage = page + 1;
          setPage(nextPage);
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
  }, [hasMore, loadingMore, page, fetchMedia]);

  // Map i18n language to locale string for date formatting
  const localeMap = { it: 'it-IT', ko: 'ko-KR', en: 'en-US' };
  const dateLocale = localeMap[i18n.language] || 'it-IT';

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600 text-lg">{t('loading_memories')}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="text-center mb-8">
        <h2 className="text-4xl wedding-title mb-2">{t('gallery_title')}</h2>
        <p className="text-gray-600 italic">{t('gallery_subtitle')}</p>
      </div>

      {/* Face group row */}
      {activeFaceGroups.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">{t('filter_by_person')}</h3>
          <div className="overflow-x-auto pb-2 scrollbar-hide">
            <div className="flex gap-3 px-2" style={{ scrollSnapType: 'x mandatory' }}>
              {activeFaceGroups.map(group => (
                <button
                  key={group.id}
                  onClick={() => setSelectedGroupId(prev => prev === group.id ? null : group.id)}
                  className={`flex flex-col items-center gap-1 flex-shrink-0 transition-transform hover:scale-105 ${
                    selectedGroupId === group.id ? 'ring-2 ring-pink-500 rounded-full' : ''
                  }`}
                  style={{ scrollSnapAlign: 'start' }}
                >
                  <img
                    src={group.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                    alt={group.user_display_name || ''}
                    className="w-12 h-12 rounded-full object-contain border-2 border-white shadow-sm"
                    onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filter controls */}
      <div className="mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">{t('Search by user')}</label>
          <select
            value={selectedUserId}
            onChange={e => setSelectedUserId(e.target.value)}
            className="wedding-input"
          >
            <option value="">{t('All users')}</option>
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.first_name || user.last_name
                  ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                  : user.username}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedGroupId && (() => {
        const group = faceGroups.find(g => g.id === selectedGroupId);
        return (
          <div className="mb-4 flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600">{t('Filtering by')}:</span>
            <span className="inline-flex items-center gap-1 bg-pink-50 rounded-full px-2 py-1">
              <img
                src={group?.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                alt=""
                className="w-6 h-6 rounded-full object-cover border border-pink-200"
                onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
              />
              <button
                onClick={() => setSelectedGroupId(null)}
                className="text-pink-600 hover:text-pink-800 text-xs leading-none"
                title={t('Remove filter')}
              >
                ✕
              </button>
            </span>
            <button
              onClick={() => setSelectedGroupId(null)}
              className="text-xs text-pink-600 underline hover:text-pink-800 ml-2"
            >
              {t('Clear filter')}
            </button>
          </div>
        );
      })()}

      {!loading && media.length === 0 ? (
        <div className="text-center py-20 wedding-card">
          <span className="text-6xl floating-heart inline-block">🌸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_photos_yet')}</p>
          <p className="text-gray-500 text-sm">{t('be_first_to_share')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {media.map((item) => {
            const isFailed = failedMediaIds.has(item.id);
            const faceTags = item.face_tags || [];

            return (
              <div key={item.id} className="gallery-item bg-white shadow-lg">
                {isFailed ? (
                  <div className="w-full aspect-square bg-gray-100 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <span className="text-4xl">🖼️‍🗑️</span>
                      <p className="text-xs mt-1">{t('file_unavailable')}</p>
                    </div>
                  </div>
                ) : (
                  <Link to={`/media/${item.id}`} state={{ media: item }} className="block relative">
                    {item.media_type === 'video' ? (
                      <video
                        src={`${API_URL}${item.file_url}`}
                        className="w-full aspect-square object-cover"
                        muted
                        preload="metadata"
                        onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                      />
                    ) : (
                      <img
                        src={`${API_URL}${item.file_url}`}
                        alt={item.caption || t('beautiful_moment')}
                        className="w-full aspect-square object-cover"
                        onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                      />
                    )}
                  </Link>
                )}
                <div className="p-3">
                  {/* Uploader info */}
                  {item.uploader_username && (
                    <div className="mb-2 flex items-center gap-1">
                      <span className="text-xs text-gray-500">{t('uploaded_by')}:</span>
                      <Link to={`/user/${item.user_id}`} className="inline-flex items-center gap-1 hover:opacity-80">
                        <img
                          src={item.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                          alt={item.uploader_username}
                          className="w-6 h-6 rounded-full object-cover border border-pink-200"
                          onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                        />
                        <span className="text-sm text-gray-600 font-medium">
                          {item.uploader_first_name || item.uploader_last_name
                            ? `${item.uploader_first_name || ''} ${item.uploader_last_name || ''}`.trim()
                            : item.uploader_username}
                        </span>
                      </Link>
                    </div>
                  )}
                  <p className="text-gray-700 text-sm mb-2 line-clamp-2">
                    {item.caption || t('beautiful_moment')}
                  </p>
                  {item.media_type === 'image' && faceTags.length > 0 && (
                    <div className="mt-2 flex items-center gap-1">
                      <span className="text-xs text-gray-500">{t('in_this_photo')}:</span>
                      <div className="inline-flex overflow-x-auto gap-1">
                        {faceTags.map(tag => (
                          <button
                            key={tag.face_group_id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedGroupId(prev => prev === tag.face_group_id ? null : tag.face_group_id);
                            }}
                            className={`flex-shrink-0 w-6 h-6 rounded-full overflow-hidden border-2 transition-colors ${
                              selectedGroupId === tag.face_group_id ? 'border-pink-500' : 'border-white'
                            }`}
                          >
                            <img
                              src={tag.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                              alt=""
                              className="w-full h-full object-cover"
                              onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-gray-500 text-xs">
                    {t('uploaded_at')}: {new Date(item.uploaded_at).toLocaleDateString(dateLocale, { day: '2-digit', month: '2-digit', year: 'numeric' })} {new Date(item.uploaded_at).toLocaleTimeString(dateLocale, { hour: '2-digit', minute: '2-digit', hour12: false })}
                  </p>
                </div>
              </div>
            );
          })}
          {hasMore && (
            <div ref={sentinelRef} className="col-span-full flex justify-center py-4">
              {loadingMore ? (
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

export default Gallery;
