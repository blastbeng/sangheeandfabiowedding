import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const Gallery = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_URL}/api/auth/media/`)
      .then(res => res.json())
      .then(data => {
        setMedia(data);
        setLoading(false);
      })
      .catch(err => {
        logger.error('[Gallery] Failed to fetch media:', err);
        logger.error('[Gallery] API URL:', API_URL);
        setLoading(false);
      });
  }, []);

  const getStatusBadge = (status) => {
    const badges = {
      pending: 'status-pending',
      approved: 'status-approved',
      rejected: 'status-rejected'
    };
    const icons = { pending: '⏳', approved: '✅', rejected: '❌' };
    return <span className={`status-badge ${badges[status]}`}>{icons[status]} {t(status)}</span>;
  };

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600 text-lg">{t('loading_memories')}</p>
        <div className="floral-divider mt-4">✿ ─────── ✿ ─────── ✿</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="text-center mb-8">
        <h2 className="text-4xl wedding-title mb-2">{t('gallery_title')}</h2>
        <p className="text-gray-600 italic">{t('gallery_subtitle')}</p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
      </div>

      {media.length === 0 ? (
        <div className="text-center py-20 wedding-card">
          <span className="text-6xl floating-heart inline-block">🌸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_photos_yet')}</p>
          <p className="text-gray-500 text-sm">{t('be_first_to_share')}</p>
          <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {media.map((item) => (
            <div key={item.id} className="gallery-item bg-white shadow-lg">
              <div className="relative">
                {item.media_type === 'video' ? (
                  <video src={`${API_URL}${item.file_url}`} className="w-full h-48 object-cover" controls />
                ) : (
                  <img src={`${API_URL}${item.file_url}`} alt={item.caption || t('beautiful_moment')} className="w-full h-48 object-cover" />
                )}
                <div className="absolute top-2 right-2">{getStatusBadge(item.status)}</div>
              </div>
              <div className="p-4">
                <p className="text-gray-700 text-sm mb-2 line-clamp-2">{item.caption || t('beautiful_moment')}</p>
                <p className="text-gray-500 text-xs">📅 {new Date(item.uploaded_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Gallery;
