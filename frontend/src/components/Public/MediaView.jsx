import { useState, useEffect } from 'react';
import { useLocation, useParams, Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const MediaView = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL;

  const [media, setMedia] = useState(location.state?.media || null);
  const [loading, setLoading] = useState(!location.state?.media);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location.state?.media) return; // already have media from state
    // Fetch media by id
    fetch(`${API_URL}/api/auth/media/public/?id=${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Media not found');
        return res.json();
      })
      .then(data => {
        // The endpoint returns an array; find the matching item
        const item = Array.isArray(data) ? data.find(m => m.id === parseInt(id)) : data;
        if (item) {
          setMedia(item);
        } else {
          setError('Media not found');
        }
      })
      .catch(err => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [id, API_URL]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-center">
        <div className="wedding-card p-8">
          <span className="text-5xl">⏳</span>
          <p className="mt-4 text-gray-600">{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (error || !media) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-center">
        <div className="wedding-card p-8">
          <span className="text-5xl">🌸</span>
          <p className="mt-4 text-gray-600">{t('media_not_found')}</p>
          <Link to="/gallery" className="text-pink-600 underline mt-2 inline-block">
            {t('back_to_gallery')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="wedding-card p-6">
        <button onClick={() => navigate(-1)} className="text-pink-600 underline mb-4 inline-block">
          ← {t('back')}
        </button>

        <div className="flex justify-center mb-6">
          {media.media_type === 'video' ? (
            <video
              src={`${API_URL}${media.file_url}`}
              controls
              className="max-w-full max-h-[70vh] rounded-lg shadow-lg"
            />
          ) : (
            <img
              src={`${API_URL}${media.file_url}`}
              alt={media.caption || t('beautiful_moment')}
              className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg"
            />
          )}
        </div>

        <div className="space-y-3">
          {media.uploader_username && (
            <div className="flex items-center gap-2">
              <img
                src={media.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                alt={media.uploader_username}
                className="w-10 h-10 rounded-full object-cover border-2 border-pink-200"
                onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
              />
              <span className="text-gray-700 font-medium">{media.uploader_username}</span>
            </div>
          )}

          {media.caption && (
            <p className="text-gray-800 text-lg">{media.caption}</p>
          )}

          {media.face_tags && media.face_tags.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-xs text-gray-500">{t('in_this_photo')}:</span>
              {media.face_tags.map(tag => (
                <div key={tag.group_id} className="flex items-center gap-1">
                  <img
                    src={tag.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                    alt=""
                    className="w-6 h-6 rounded-full object-cover border border-pink-200"
                    onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                  />
                  {tag.user_display_name && (
                    <span className="text-xs text-gray-600">{tag.user_display_name}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="text-gray-500 text-sm">
            📅 {new Date(media.uploaded_at).toLocaleDateString()}
          </p>
        </div>
      </div>
    </div>
  );
};

export default MediaView;
