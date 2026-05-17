import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';
import ThumbnailImage from '../Common/ThumbnailImage';

const MyUploads = () => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(null); // null = unknown
  const [fetching, setFetching] = useState(false);
  const [fetchId, setFetchId] = useState(0); // increment to force refetch
  const [selectedIds, setSelectedIds] = useState([]);
  const [message, setMessage] = useState(null);
  const [viewMode, setViewMode] = useState('gallery');
  const [failedMediaIds, setFailedMediaIds] = useState(new Set());
  const API_URL = import.meta.env.VITE_API_URL;

  // Auto-dismiss messages after 4 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const refreshUploads = () => {
    setPage(1);
    setFetchId(prev => prev + 1);
  };

  // Data fetching
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      setFetching(true);
      try {
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('page_size', pageSize);
        const res = await authFetch(`${API_URL}/api/auth/media/my-uploads/?${params}`);
        if (cancelled) return;

        if (!res.ok) {
          logger.warn('[MyUploads] Fetch failed:', res.status);
          setUploads([]);
          setTotalCount(0);
          return;
        }

        const data = await res.json();
        const results = Array.isArray(data) ? data : (data.results || []);
        const count = (data && typeof data === 'object' && !Array.isArray(data))
          ? data.count
          : undefined;

        if (!cancelled) {
          setUploads(results);
          setFailedMediaIds(new Set());
          if (count !== undefined) setTotalCount(count);
          else setTotalCount(null);

          // If current page is empty and not the first page, go back one page
          if (results.length === 0 && page > 1) {
            setPage(prev => prev - 1);
          }
        }
      } catch (err) {
        if (!cancelled) {
          logger.error('[MyUploads] Fetch error:', err);
          setUploads([]);
          setTotalCount(0);
        }
      } finally {
        if (!cancelled) {
          setFetching(false);
          setLoading(false);
        }
      }
    };

    fetchData();
    return () => { cancelled = true; };
  }, [page, pageSize, fetchId, API_URL]);

  const totalPages = totalCount !== null ? Math.ceil(totalCount / pageSize) : null;

  const handleDelete = async (id) => {
    if (!confirm(t('my_uploads_delete_confirm'))) return;
    try {
      const res = await authFetch(`${API_URL}/api/auth/media/${id}/`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setMessage({ type: 'success', text: t('my_uploads_delete_success') });
        refreshUploads();
      } else {
        const errData = await res.json().catch(() => ({}));
        setMessage({ type: 'error', text: errData.error || t('my_uploads_delete_error') });
      }
    } catch (err) {
      logger.error('[MyUploads] Delete failed for ID:', id, err);
      setMessage({ type: 'error', text: t('my_uploads_delete_error') });
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === uploads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(uploads.map(u => u.id));
    }
  };

  const toggleSelectItem = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(t('my_uploads_bulk_delete_confirm', { count: selectedIds.length }))) return;
    try {
      const res = await authFetch(`${API_URL}/api/auth/media/bulk-delete/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_ids: selectedIds })
      });
      if (res.ok) {
        let message = t('my_uploads_bulk_delete_success');
        try {
          const data = await res.json();
          if (data.message) message = data.message;
        } catch (_) {
          // response had no JSON body (e.g., 204 No Content) – use default message
        }
        setMessage({ type: 'success', text: message });
        setSelectedIds([]);
        refreshUploads();
      } else {
        const errData = await res.json().catch(() => ({}));
        setMessage({ type: 'error', text: errData.error || t('my_uploads_bulk_delete_error') });
      }
    } catch (err) {
      logger.error('[MyUploads] Bulk delete failed:', err);
      setMessage({ type: 'error', text: t('my_uploads_bulk_delete_error') });
    }
  };

  const getStatusBadge = (status) => {
    const badges = { pending: 'status-pending', approved: 'status-approved', rejected: 'status-rejected' };
    const icons = { pending: '⏳', approved: '✅', rejected: '❌' };
    return <span className={`status-badge ${badges[status]} whitespace-nowrap`}>{icons[status]} {t(status)}</span>;
  };

  if (loading) {
    return (
      <div className="text-center py-10">
        <span className="text-4xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">{t('my_uploads_loading')}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">{t('my_uploads_title')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">{t('my_uploads_subtitle')}</p>

        {/* Feedback message */}
        {message && (
          <div className={`mb-4 p-3 rounded-lg text-center ${
            message.type === 'success' 
              ? 'bg-green-100 text-green-800 border border-green-300' 
              : 'bg-red-100 text-red-800 border border-red-300'
          }`}>
            {message.text}
          </div>
        )}

        {uploads.length === 0 && page === 1 ? (
          <div className="text-center py-10">
            <span className="text-6xl floating-heart inline-block">📸</span>
            <p className="mt-4 text-gray-600 text-lg">{t('my_uploads_no_uploads')}</p>
            <p className="text-gray-500 text-sm">{t('my_uploads_share_first')}</p>
            <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
            <Link to="/upload" className="wedding-btn inline-block mt-4">{t('my_uploads_upload_now')}</Link>
          </div>
        ) : (
          <>
            {/* View mode toggle and bulk actions */}
            <div className="flex justify-between items-center mb-4">
              <div className="inline-flex rounded-md shadow-sm" role="group">
                <button
                  type="button"
                  onClick={() => setViewMode('gallery')}
                  className={`px-4 py-2 text-sm font-medium rounded-l-lg border ${
                    viewMode === 'gallery'
                      ? '!bg-pink-500 !text-white !border-pink-500'
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
                      ? '!bg-pink-500 !text-white !border-pink-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  📋 {t('table_view')}
                </button>
              </div>
              {selectedIds.length > 0 && (
                <button
                  onClick={handleBulkDelete}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm"
                >
                  {t('my_uploads_delete_selected', { count: selectedIds.length })}
                </button>
              )}
            </div>

            {viewMode === 'table' ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-pink-200">
                      <th className="py-3 w-10">
                        <input
                          type="checkbox"
                          checked={selectedIds.length === uploads.length && uploads.length > 0}
                          onChange={toggleSelectAll}
                          className="w-4 h-4 accent-pink-500"
                        />
                      </th>
                      <th className="text-left py-3 text-pink-600 whitespace-nowrap">{t('my_uploads_preview')}</th>
                      <th className="text-left py-3 text-pink-600 whitespace-nowrap">{t('my_uploads_caption')}</th>
                      <th className="text-left py-3 text-pink-600 whitespace-nowrap">{t('my_uploads_uploaded')}</th>
                      <th className="text-left py-3 text-pink-600 whitespace-nowrap">{t('my_uploads_status')}</th>
                      <th className="text-left py-3 text-pink-600 whitespace-nowrap">{t('my_uploads_actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uploads.map((upload) => (
                      <tr key={upload.id} className="border-b border-pink-100 hover:bg-pink-50">
                        <td className="py-3">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(upload.id)}
                            onChange={() => toggleSelectItem(upload.id)}
                            className="w-4 h-4 accent-pink-500"
                          />
                        </td>
                        <td className="py-3">
                          {upload.file_url ? (
                            failedMediaIds.has(upload.id) ? (
                              <div className="w-16 h-16 bg-gray-100 rounded-lg border-2 border-pink-200 flex items-center justify-center text-gray-400 text-xs">
                                {t('file_unavailable')}
                              </div>
                            ) : (
                              <ThumbnailImage
                                mediaId={upload.id}
                                apiUrl={API_URL}
                                alt={t('my_uploads_preview_alt')}
                                className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200"
                                mediaType={upload.media_type}
                                onFinalError={(id) => setFailedMediaIds(prev => new Set(prev).add(id))}
                              />
                            )
                          ) : (
                            <div className="w-16 h-16 bg-gray-100 rounded-lg border-2 border-pink-200 flex items-center justify-center text-gray-400 text-xs">
                              {t('file_unavailable')}
                            </div>
                          )}
                        </td>
                        <td className="py-3 text-gray-700 whitespace-nowrap">{upload.caption || '-'}</td>
                        <td className="py-3 text-gray-600 text-sm whitespace-nowrap">{new Date(upload.uploaded_at).toLocaleDateString()}</td>
                        <td className="py-3 whitespace-nowrap">{getStatusBadge(upload.status)}</td>
                        <td className="py-3 whitespace-nowrap">
                          <button onClick={() => handleDelete(upload.id)} className="text-red-500 hover:text-red-700 text-sm">{t('my_uploads_delete_button')}</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Gallery view */
              <>
                <div className="flex items-center mb-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === uploads.length && uploads.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 text-wedding-600 border-gray-300 rounded focus:ring-wedding-500"
                  />
                  <span className="ml-2 text-sm text-gray-600">{t('select_all')}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {uploads.map((upload) => (
                    <div
                      key={upload.id}
                      className={`bg-white rounded-lg shadow overflow-hidden relative cursor-pointer border-2 ${
                        selectedIds.includes(upload.id) ? 'border-wedding-600' : 'border-transparent'
                      }`}
                      onClick={() => toggleSelectItem(upload.id)}
                    >
                      {/* Checkbox overlay */}
                      <div className="absolute top-2 left-2 z-10">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(upload.id)}
                          onChange={() => toggleSelectItem(upload.id)}
                          onClick={(e) => e.stopPropagation()}
                          className="w-4 h-4 text-wedding-600 border-gray-300 rounded focus:ring-wedding-500"
                        />
                      </div>
                      {/* Media preview */}
                      <div className="aspect-w-1 aspect-h-1 bg-gray-200">
                        {upload.file_url ? (
                          failedMediaIds.has(upload.id) ? (
                            <div className="flex items-center justify-center h-full text-gray-400">
                              <div className="text-center">
                                <span className="text-4xl">🖼️‍🗑️</span>
                                <p className="text-xs mt-1">{t('file_unavailable')}</p>
                              </div>
                            </div>
                          ) : (
                            <ThumbnailImage
                              mediaId={upload.id}
                              apiUrl={API_URL}
                              alt={upload.caption || t('beautiful_moment')}
                              className="object-cover w-full h-full"
                              mediaType={upload.media_type}
                              onFinalError={(id) => setFailedMediaIds(prev => new Set(prev).add(id))}
                            />
                          )
                        ) : (
                          <div className="flex items-center justify-center h-full text-gray-400">🎬</div>
                        )}
                      </div>
                      {/* Info and actions */}
                      <div className="p-3">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {upload.caption || t('no_caption')}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          {getStatusBadge(upload.status)}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(upload.id);
                            }}
                            className="text-red-500 hover:text-red-700 text-sm"
                          >
                            {t('my_uploads_delete_button')}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Pagination */}
            <div className="flex flex-wrap items-center justify-between gap-2 mt-4">
              <div className="flex items-center gap-2">
                <label htmlFor="pageSize" className="text-sm text-gray-600">
                  {t('show')}
                </label>
                <select
                  id="pageSize"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
                  }}
                  className="wedding-input text-sm"
                  disabled={fetching}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>

              <div className="flex flex-nowrap items-center gap-0.5">
                <button
                  onClick={() => setPage(1)}
                  disabled={page === 1 || fetching}
                  className="inline-flex items-center justify-center text-xs font-medium rounded border border-pink-300 bg-white text-pink-700 hover:bg-pink-50 disabled:opacity-50 min-w-[40px] min-h-[40px] px-2 py-1"
                >
                  ««
                </button>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1 || fetching}
                  className="inline-flex items-center justify-center text-xs font-medium rounded border border-pink-300 bg-white text-pink-700 hover:bg-pink-50 disabled:opacity-50 min-w-[40px] min-h-[40px] px-2 py-1"
                >
                  ‹
                </button>
                {totalCount !== null && (
                  <span className="text-sm text-gray-700">
                    {t('page_x_of_y', { current: page, total: totalPages })}
                  </span>
                )}
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={
                    fetching ||
                    (totalCount !== null
                      ? page * pageSize >= totalCount
                      : uploads.length < pageSize)
                  }
                  className="inline-flex items-center justify-center text-xs font-medium rounded border border-pink-300 bg-white text-pink-700 hover:bg-pink-50 disabled:opacity-50 min-w-[40px] min-h-[40px] px-2 py-1"
                >
                  ›
                </button>
                <button
                  onClick={() => setPage(totalPages !== null ? totalPages : page + 1)}
                  disabled={
                    fetching ||
                    (totalCount !== null
                      ? page * pageSize >= totalCount
                      : uploads.length < pageSize)
                  }
                  className="inline-flex items-center justify-center text-xs font-medium rounded border border-pink-300 bg-white text-pink-700 hover:bg-pink-50 disabled:opacity-50 min-w-[40px] min-h-[40px] px-2 py-1"
                >
                  »»
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MyUploads;
