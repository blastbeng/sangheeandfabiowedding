import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';
import logger from '../../utils/logger';
import ThumbnailImage from '../Common/ThumbnailImage';

const API_URL = import.meta.env.VITE_API_URL;

const WeddingBook = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const [bookId, setBookId] = useState(() => localStorage.getItem('weddingBookId') || null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState('');
  const [pastBooks, setPastBooks] = useState([]);
  const [selectedBookIds, setSelectedBookIds] = useState([]);
  const [viewMode, setViewMode] = useState('gallery'); // 'gallery' | 'table'
  const pollingRef = useRef(null);

  // Loading/error states for media
  const [mediaLoading, setMediaLoading] = useState(true);
  const [mediaError, setMediaError] = useState('');

  const MIN_MEDIA = 20;

  // Fetch approved media
  useEffect(() => {
    setMediaLoading(true);
    setMediaError('');
    authFetch(`${API_URL}/api/auth/media/public/?status=approved&page_size=10000&ordering=similarity`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        // Only images are allowed in the wedding book
        const imagesOnly = Array.isArray(data)
          ? data.filter(item => item.media_type === 'image')
          : [];
        setMedia(imagesOnly);
        setMediaLoading(false);
      })
      .catch(err => {
        logger.error('[WeddingBook] Failed to fetch media:', err);
        setMediaError(t('Failed to load media. Please try again.'));
        setMediaLoading(false);
      });
  }, [API_URL, t]);

  // Fetch users with approved media for filter
  useEffect(() => {
    authFetch(`${API_URL}/api/auth/users/public/?has_approved_media=true`)
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(err => logger.error('[WeddingBook] Failed to fetch users:', err));
  }, []);

  // Fetch past books
  const fetchPastBooks = useCallback(() => {
    authFetch(`${API_URL}/api/auth/admin/wedding-book/`)
      .then(res => res.json())
      .then(data => setPastBooks(data))
      .catch(err => logger.error('[WeddingBook] Failed to fetch past books:', err));
  }, []);

  useEffect(() => {
    fetchPastBooks();
  }, [fetchPastBooks]);

  // Polling logic
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
          fetchPastBooks(); // refresh list
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

  useEffect(() => {
    if (bookId) {
      fetchBookStatus(bookId);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [bookId, fetchBookStatus]);

  // Filter media by selected user
  const filteredMedia = selectedUserId
    ? media.filter(item => item.user_id === parseInt(selectedUserId))
    : media;

  // Toggle individual selection
  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  // Keep selectAll checkbox in sync with individual selections
  useEffect(() => {
    if (selectedIds.length === filteredMedia.length && filteredMedia.length > 0) {
      setSelectAll(true);
    } else {
      setSelectAll(false);
    }
  }, [selectedIds, filteredMedia]);

  // Select All / Deselect All
  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedIds([]);
      setSelectAll(false);
    } else {
      const allIds = filteredMedia.map(item => item.id);
      setSelectedIds(allIds);
      setSelectAll(true);
    }
  };

  // Start generation (now always allowed if total approved >= 20)
  const startGeneration = async () => {
    setStatus('generating');
    setProgress(0);
    setError('');
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/generate/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_ids: selectedIds }), // can be empty
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

  const handleSelectBook = (id) => {
    setSelectedBookIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSelectAllBooks = () => {
    if (selectedBookIds.length === pastBooks.length) {
      setSelectedBookIds([]);
    } else {
      setSelectedBookIds(pastBooks.map(b => b.id));
    }
  };

  const handleBulkDeleteBooks = async () => {
    if (selectedBookIds.length === 0) return;
    if (!confirm(t('Delete selected wedding books?'))) return;
    for (const id of selectedBookIds) {
      try {
        await authFetch(`${API_URL}/api/auth/admin/wedding-book/${id}/delete/`, { method: 'DELETE' });
      } catch (err) {
        logger.error('[WeddingBook] Bulk delete error for book', id, err);
      }
    }
    setSelectedBookIds([]);
    fetchPastBooks();
    // If the active book was deleted, clear it
    if (bookId && selectedBookIds.includes(bookId)) {
      handleNewBook();
    }
  };

  const handleDeleteBook = async (id) => {
    if (!confirm(t('Delete this wedding book?'))) return;
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/wedding-book/${id}/delete/`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchPastBooks();
        // If the deleted book was the active one, clear it
        if (bookId === id) {
          handleNewBook();
        }
      }
    } catch (err) {
      logger.error('[WeddingBook] Delete book error:', err);
    }
  };

  const totalApproved = media.length;
  const canGenerate = !mediaLoading && totalApproved >= MIN_MEDIA;

  return (
    <div className="wedding-card p-6">
      <h2 className="text-2xl wedding-title mb-4">{t('Wedding Book')}</h2>

      {/* Info message */}
      <p className="text-sm text-gray-600 mb-4">
        {t('Select at least {min} images. If you select fewer, AI will automatically choose the best ones to reach {min}.', { min: MIN_MEDIA })}
      </p>

      {/* User filter */}
      <div className="mb-4">
        <label className="mr-2 text-sm">{t('Filter by user')}:</label>
        <select
          value={selectedUserId}
          onChange={(e) => setSelectedUserId(e.target.value)}
          className="wedding-input"
        >
          <option value="">{t('All users')}</option>
          {users.map(u => (
            <option key={u.id} value={u.id}>
              {u.first_name || u.last_name
                ? `${u.first_name || ''} ${u.last_name || ''}`.trim()
                : u.username}
            </option>
          ))}
        </select>
      </div>

      {/* Buttons and progress bar */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto whitespace-nowrap pb-2">
        <button
          onClick={startGeneration}
          disabled={status === 'generating' || !canGenerate}
          className="px-4 py-2 bg-pink-500 text-white rounded disabled:opacity-50 flex items-center gap-2 flex-shrink-0"
        >
          {status === 'generating' ? (
            <>
              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
              {t('Generating...')}
            </>
          ) : (
            t('Generate Wedding Book')
          )}
        </button>
        {bookId && (
          <button onClick={handleNewBook} className="px-4 py-2 bg-gray-200 text-gray-700 rounded flex-shrink-0">
            {t('New Book')}
          </button>
        )}
        <button
          onClick={handleSelectAll}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded flex-shrink-0"
        >
          {selectAll ? t('Deselect All') : t('Select All')}
        </button>
        <span className="text-sm text-gray-500 ml-2 flex-shrink-0">
          {selectedIds.length} / {MIN_MEDIA} {t('selected')}
        </span>
      </div>
      {!canGenerate && !mediaLoading && (
        <p className="text-sm text-red-500 mt-1">
          {t('Need at least 20 approved media. Currently: {count}', { count: totalApproved })}
        </p>
      )}

      {/* View mode toggle */}
      <div className="flex justify-end mb-4">
        <div className="inline-flex rounded-md shadow-sm" role="group">
          <button
            type="button"
            onClick={() => setViewMode('gallery')}
            className={`px-4 py-2 text-sm font-medium rounded-l-lg border ${
              viewMode === 'gallery'
                ? 'bg-pink-500 text-white border-pink-500'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            🖼️ {t('gallery_view')}
          </button>
          <button
            type="button"
            onClick={() => setViewMode('table')}
            className={`px-4 py-2 text-sm font-medium rounded-r-lg border-t border-b border-r ${
              viewMode === 'table'
                ? 'bg-pink-500 text-white border-pink-500'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            📋 {t('table_view')}
          </button>
        </div>
      </div>

      {status === 'generating' && (
        <div className="mt-4 w-full max-w-full overflow-hidden">
          <progress value={progress} max="100" className="w-full" />
          <span className="text-sm">{progress}%</span>
        </div>
      )}

      {status === 'completed' && (
        <div className="mt-4">
          <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-pink-500 text-white rounded mr-2">
            {t('Download PDF')}
          </a>
          <button onClick={handleRegenerate} className="px-4 py-2 bg-pink-500 text-white rounded">
            {t('Regenerate')}
          </button>
        </div>
      )}

      {status === 'failed' && (
        <div className="mt-4 text-red-600">
          <p>{error}</p>
          <button onClick={handleRegenerate} className="px-4 py-2 bg-pink-500 text-white rounded mt-2">
            {t('Retry')}
          </button>
        </div>
      )}

      {/* Past Wedding Books */}
      <div className="mt-8">
        <h3 className="text-xl wedding-title mb-2">{t('Previously Generated Books')}</h3>
        {pastBooks.length === 0 ? (
          <p className="text-gray-500">{t('No books generated yet.')}</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="mb-2">
              <button
                onClick={handleBulkDeleteBooks}
                disabled={selectedBookIds.length === 0}
                className="px-3 py-1 bg-red-500 text-white rounded disabled:opacity-50 text-sm"
              >
                {t('Delete')} ({selectedBookIds.length})
              </button>
            </div>
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-2 py-1 text-left">
                    <input
                      type="checkbox"
                      checked={selectedBookIds.length === pastBooks.length && pastBooks.length > 0}
                      onChange={handleSelectAllBooks}
                    />
                  </th>
                  <th className="px-2 py-1 text-left">{t('ID')}</th>
                  <th className="px-2 py-1 text-left">{t('Status')}</th>
                  <th className="px-2 py-1 text-left">{t('Progress')}</th>
                  <th className="px-2 py-1 text-left">{t('Media Count')}</th>
                  <th className="px-2 py-1 text-left">{t('File Size')}</th>
                  <th className="px-2 py-1 text-left">{t('Created')}</th>
                  <th className="px-2 py-1 text-left">{t('Actions')}</th>
                </tr>
              </thead>
              <tbody>
                {pastBooks.map(book => (
                  <tr key={book.id} className="border-t">
                    <td className="px-2 py-1">
                      <input
                        type="checkbox"
                        checked={selectedBookIds.includes(book.id)}
                        onChange={() => handleSelectBook(book.id)}
                      />
                    </td>
                    <td className="px-2 py-1">{book.id}</td>
                    <td className="px-2 py-1">{book.status}</td>
                    <td className="px-2 py-1">{book.progress}%</td>
                    <td className="px-2 py-1">{book.media_count}</td>
                    <td className="px-2 py-1">{book.file_size || '—'}</td>
                    <td className="px-2 py-1">{new Date(book.created_at).toLocaleDateString()}</td>
                    <td className="px-2 py-1">
                      {book.status === 'completed' && book.download_url && (
                        <a href={book.download_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline mr-2">
                          {t('Download')}
                        </a>
                      )}
                      <button
                        onClick={() => handleDeleteBook(book.id)}
                        className="text-red-600 hover:underline"
                      >
                        {t('Delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Media selection grid / table */}
      {mediaLoading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500 mx-auto"></div>
          <p className="text-gray-500 mt-2">{t('Loading media...')}</p>
        </div>
      ) : mediaError ? (
        <div className="text-center py-8">
          <p className="text-red-500 mb-2">{mediaError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-gray-200 rounded"
          >
            {t('Retry')}
          </button>
        </div>
      ) : filteredMedia.length === 0 ? (
        <div className="text-center py-8 text-gray-500">{t('No approved media found.')}</div>
      ) : viewMode === 'table' ? (
        /* ---------- TABLE VIEW ---------- */
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-pink-200">
                <th className="text-left py-3 text-pink-600">
                  <input type="checkbox" checked={selectAll} onChange={handleSelectAll} />
                </th>
                <th className="text-left py-3 text-pink-600">{t('admin_mod_col_preview')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_mod_col_user')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_mod_col_caption')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_mod_col_date')}</th>
              </tr>
            </thead>
            <tbody>
              {filteredMedia.map((item) => (
                <tr key={item.id} className="border-b border-pink-100 hover:bg-pink-50">
                  <td className="py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelect(item.id)}
                    />
                  </td>
                  <td className="py-3">
                    <ThumbnailImage
                      mediaId={item.id}
                      apiUrl={API_URL}
                      alt={item.caption || t('beautiful_moment')}
                      className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200"
                      mediaType={item.media_type}
                    />
                  </td>
                  <td className="py-3 text-gray-700">
                    {item.username || item.user__username || t('unknown')}
                  </td>
                  <td className="py-3 text-gray-600 text-sm">{item.caption || '-'}</td>
                  <td className="py-3 text-gray-600 text-sm">
                    {new Date(item.uploaded_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* ---------- GALLERY VIEW ---------- */
        <>
          {/* Select All checkbox for gallery mode */}
          <div className="flex items-center mb-2">
            <input
              type="checkbox"
              checked={selectAll}
              onChange={handleSelectAll}
              className="w-4 h-4 text-wedding-600 border-gray-300 rounded focus:ring-wedding-500"
            />
            <span className="ml-2 text-sm text-gray-600">{t('select_all')}</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-4">
            {filteredMedia.map(item => (
              <div
                key={item.id}
                className={`cursor-pointer border-2 ${selectedIds.includes(item.id) ? 'border-wedding-azure' : 'border-transparent'}`}
                onClick={() => toggleSelect(item.id)}
              >
                <div className="aspect-w-1 aspect-h-1 bg-gray-200">
                  <ThumbnailImage
                    mediaId={item.id}
                    apiUrl={API_URL}
                    alt={item.caption || t('beautiful_moment')}
                    className="object-cover w-full h-full"
                    mediaType={item.media_type}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

    </div>
  );
};

export default WeddingBook;
