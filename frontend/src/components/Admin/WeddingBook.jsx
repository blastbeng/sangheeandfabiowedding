import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';
import logger from '../../utils/logger';

const API_URL = import.meta.env.VITE_API_URL;

const WeddingBook = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bookId, setBookId] = useState(() => {
    return localStorage.getItem('weddingBookId') || null;
  });
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState('');
  const pollingRef = useRef(null);

  const MIN_MEDIA = 20;

  // Fetch approved media for selection
  useEffect(() => {
    authFetch(`${API_URL}/api/auth/media/public/?status=approved&page_size=1000`)
      .then(res => res.json())
      .then(data => setMedia(data))
      .catch(err => logger.error('[WeddingBook] Failed to fetch media:', err));
  }, []);

  const startPolling = (id) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      try {
        const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/status/${id}/`);
        const data = await res.json();
        setProgress(data.progress);
        if (data.status === 'completed') {
          clearInterval(pollingRef.current);
          setStatus('completed');
          setDownloadUrl(data.download_url);
        } else if (data.status === 'failed') {
          clearInterval(pollingRef.current);
          setStatus('failed');
          setError(data.error_message || 'Generation failed');
        }
      } catch (err) {
        logger.error('[WeddingBook] Polling error:', err);
      }
    }, 2000);
  };

  const fetchBookStatus = useCallback(async (id) => {
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/status/${id}/`);
      const data = await res.json();
      setProgress(data.progress);
      if (data.selected_media_ids) {
        setSelectedIds(data.selected_media_ids);
      }
      if (data.status === 'completed') {
        setStatus('completed');
        setDownloadUrl(data.download_url);
      } else if (data.status === 'failed') {
        setStatus('failed');
        setError(data.error_message || 'Generation failed');
      } else {
        setStatus('generating');
        startPolling(id);
      }
    } catch (err) {
      logger.error('[WeddingBook] Fetch status error:', err);
      localStorage.removeItem('weddingBookId');
      setBookId(null);
    }
  }, []);

  // On mount, if a bookId exists, fetch its status and resume polling
  useEffect(() => {
    if (bookId) {
      fetchBookStatus(bookId);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [bookId, fetchBookStatus]);

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const startGeneration = async () => {
    if (selectedIds.length === 0) return;
    setStatus('generating');
    setProgress(0);
    setError('');
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/generate/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_ids: selectedIds }),
      });
      const data = await res.json();
      if (res.ok) {
        setBookId(data.id);
        localStorage.setItem('weddingBookId', data.id);
        startPolling(data.id);
      } else {
        setError(data.error || 'Failed to start generation');
        setStatus('failed');
      }
    } catch (err) {
      setError('Network error');
      setStatus('failed');
    }
  };

  const handleRegenerate = async () => {
    if (!bookId) return;
    if (selectedIds.length === 0) {
      setError('Please select at least one media item.');
      return;
    }
    setStatus('generating');
    setProgress(0);
    setError('');
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/regenerate/${bookId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_ids: selectedIds }),
      });
      if (res.ok) {
        startPolling(bookId);
      } else {
        const data = await res.json();
        setError(data.error || 'Regeneration failed');
        setStatus('failed');
      }
    } catch (err) {
      setError('Network error');
      setStatus('failed');
    }
  };

  const handleNewBook = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    localStorage.removeItem('weddingBookId');
    setBookId(null);
    setStatus('idle');
    setProgress(0);
    setDownloadUrl(null);
    setError('');
    setSelectedIds([]);
  };

  const totalApproved = media.length;
  const canGenerate = totalApproved >= MIN_MEDIA;

  return (
    <div className="wedding-card p-6">
      <h2 className="text-2xl wedding-title mb-4">{t('Wedding Book')}</h2>

      {/* Info message */}
      <p className="text-sm text-gray-600 mb-4">
        {t('Select at least {min} images. If you select fewer, AI will automatically choose the best ones to reach {min}.', { min: MIN_MEDIA })}
      </p>

      {/* Buttons and progress bar – moved to top */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={startGeneration}
          disabled={status === 'generating' || !canGenerate}
          className="px-4 py-2 bg-wedding-navy text-white rounded disabled:opacity-50"
        >
          {t('Generate Wedding Book')}
        </button>
        {bookId && (
          <button onClick={handleNewBook} className="px-4 py-2 bg-gray-500 text-white rounded">
            {t('New Book')}
          </button>
        )}
        <span className="text-sm text-gray-500 ml-2">
          {selectedIds.length} / {MIN_MEDIA} {t('selected')}
        </span>
      </div>

      {status === 'generating' && (
        <div className="mt-4">
          <progress value={progress} max="100" className="w-full" />
          <span>{progress}%</span>
        </div>
      )}

      {status === 'completed' && (
        <div className="mt-4">
          <a href={downloadUrl} download className="px-4 py-2 bg-green-600 text-white rounded mr-2">
            {t('Download PDF')}
          </a>
          <button onClick={handleRegenerate} className="px-4 py-2 bg-yellow-500 text-white rounded">
            {t('Regenerate')}
          </button>
        </div>
      )}

      {status === 'failed' && (
        <div className="mt-4 text-red-600">
          <p>{error}</p>
          <button onClick={handleRegenerate} className="px-4 py-2 bg-yellow-500 text-white rounded mt-2">
            {t('Retry')}
          </button>
        </div>
      )}

      {/* Media selection grid – remains below */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {media.map(item => (
          <div
            key={item.id}
            className={`cursor-pointer border-2 ${selectedIds.includes(item.id) ? 'border-wedding-azure' : 'border-transparent'}`}
            onClick={() => toggleSelect(item.id)}
          >
            <img src={`${API_URL}/api/auth/media/${item.id}/thumbnail/`} alt="" className="w-full h-32 object-cover" />
          </div>
        ))}
      </div>
    </div>
  );
};

export default WeddingBook;
