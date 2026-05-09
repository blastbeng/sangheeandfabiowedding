import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const Gallery = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    user_search: ''
  });
  const [selectedFaceTag, setSelectedFaceTag] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = () => {
    const params = new URLSearchParams();
    if (filters.user_search) params.append('user_search', filters.user_search);
    if (selectedFaceTag) params.append('facetag', selectedFaceTag);

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
  }, [filters, selectedFaceTag]);

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
      </div>

      {selectedFaceTag && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm text-gray-600">
            {t('Filtering by')}: <strong>{selectedFaceTag}</strong>
          </span>
          <button
            onClick={() => setSelectedFaceTag('')}
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
                {/* Uploader info */}
                {item.uploader_username && (
                  <div className="flex items-center gap-2 mb-2">
                    <img
                      src={item.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                      alt={item.uploader_username}
                      className="w-8 h-8 rounded-full object-cover border border-pink-200"
                      onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                    />
                    <span className="text-sm text-gray-600 font-medium">{item.uploader_username}</span>
                  </div>
                )}
                <p className="text-gray-700 text-sm mb-2 line-clamp-2">
                  {item.caption || t('beautiful_moment')}
                </p>
                {item.face_tags && item.face_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.face_tags.map(tag => (
                      <button
                        key={tag}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFaceTag(prev => prev === tag ? '' : tag);
                        }}
                        className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                          selectedFaceTag === tag
                            ? 'bg-pink-500 text-white border-pink-500'
                            : 'bg-pink-50 text-pink-700 border-pink-200 hover:bg-pink-100'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-gray-500 text-xs">
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

export default Gallery;
