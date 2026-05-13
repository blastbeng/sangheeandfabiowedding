import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import logger from '../../utils/logger';

const Gallery = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    user_search: ''
  });
  const [faceGroups, setFaceGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [captionFilter, setCaptionFilter] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = () => {
    const params = new URLSearchParams();
    if (filters.user_search) params.append('user_search', filters.user_search);
    if (selectedGroupId) params.append('face_group_id', selectedGroupId);
    if (captionFilter) params.append('caption', captionFilter);

    fetch(`${API_URL}/api/auth/media/public/?${params}`)
      .then(res => res.json())
      .then(data => {
        setMedia(data);
        setLoading(false);
      })
      .catch(err => {
        logger.error('[Gallery] Failed to fetch media:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMedia();
  }, [filters, selectedGroupId, captionFilter]);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/face-groups/`)
      .then(res => res.json())
      .then(data => setFaceGroups(data))
      .catch(err => logger.error('[Gallery] Failed to fetch face groups:', err));
  }, []);

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
      {faceGroups.length > 0 && (() => {
        // Deduplicate by thumbnail_url – keep only the first occurrence of each unique thumbnail
        const seenThumbnails = new Set();
        const uniqueGroups = faceGroups.filter(group => {
          const thumb = group.thumbnail_url || '';
          if (seenThumbnails.has(thumb)) return false;
          seenThumbnails.add(thumb);
          return true;
        });

        if (uniqueGroups.length === 0) return null;

        return (
          <div className="mb-6 overflow-x-auto pb-2 scrollbar-hide">
            <div className="flex gap-3 px-2" style={{ scrollSnapType: 'x mandatory' }}>
              {uniqueGroups.map(group => (
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
                    alt={group.name || `Person ${group.id}`}
                    className="w-10 h-10 rounded-full object-cover border-2 border-white shadow-sm"
                    onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                  />
                  <span className="text-xs text-gray-600 whitespace-nowrap">{group.name || `#${group.id}`}</span>
                </button>
              ))}
            </div>
          </div>
        );
      })()}

      {/* Filter controls */}
      <div className="mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">{t('Search by user')}</label>
          <input
            type="text"
            value={filters.user_search}
            onChange={e => setFilters({ ...filters, user_search: e.target.value })}
            className="wedding-input"
            placeholder={t('Username or name...')}
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">{t('Search by caption')}</label>
          <input
            type="text"
            value={captionFilter}
            onChange={e => setCaptionFilter(e.target.value)}
            className="wedding-input"
            placeholder={t('Caption...')}
          />
        </div>
      </div>

      {selectedGroupId && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm text-gray-600">
            {t('Filtering by')}: <strong>{faceGroups.find(g => g.id === selectedGroupId)?.name || `#${selectedGroupId}`}</strong>
          </span>
          <button
            onClick={() => setSelectedGroupId(null)}
            className="text-xs text-pink-600 underline hover:text-pink-800"
          >
            {t('Clear filter')}
          </button>
        </div>
      )}

      {media.length === 0 ? (
        <div className="text-center py-20 wedding-card">
          <span className="text-6xl floating-heart inline-block">🌸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_photos_yet')}</p>
          <p className="text-gray-500 text-sm">{t('be_first_to_share')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {media.map((item) => {
            const uniqueFaceTags = item.face_tags
              ? item.face_tags.filter(
                  (tag, index, self) => index === self.findIndex(t => t.group_id === tag.group_id)
                )
              : [];

            return (
              <div key={item.id} className="gallery-item bg-white shadow-lg">
                <Link to={`/media/${item.id}`} state={{ media: item }} className="block relative">
                  {item.media_type === 'video' ? (
                    <video
                      src={`${API_URL}${item.file_url}`}
                      className="w-full h-48 object-cover"
                      muted
                      preload="metadata"
                    />
                  ) : (
                    <img
                      src={`${API_URL}${item.file_url}`}
                      alt={item.caption || t('beautiful_moment')}
                      className="w-full h-48 object-cover"
                    />
                  )}
                </Link>
                <div className="p-4">
                  {/* Uploader info */}
                  {item.uploader_username && (
                    <div className="mb-2">
                      <span className="text-xs text-gray-500">{t('uploaded_by')}:</span>
                      <Link to={`/user/${item.user_id}`} className="flex items-center gap-2 mt-1 hover:opacity-80">
                        <img
                          src={item.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                          alt={item.uploader_username}
                          className="w-8 h-8 rounded-full object-cover border border-pink-200"
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
                  {item.media_type === 'image' && uniqueFaceTags.length > 0 && (
                    <div className="mt-2">
                      <span className="text-xs text-gray-500">{t('in_this_photo')}:</span>
                      <div className="flex overflow-x-auto gap-1 mt-1">
                        {uniqueFaceTags.map(tag => (
                          <button
                            key={tag.group_id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedGroupId(prev => prev === tag.group_id ? null : tag.group_id);
                            }}
                            className={`flex-shrink-0 w-8 h-8 rounded-full overflow-hidden border-2 transition-colors ${
                              selectedGroupId === tag.group_id ? 'border-pink-500' : 'border-white'
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
                    {t('uploaded_at')}: {new Date(item.uploaded_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })} {new Date(item.uploaded_at).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', hour12: false })}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Gallery;
