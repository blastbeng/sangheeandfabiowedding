import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const AdminModeration = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: 'pending', media_type: '' });
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const [viewMode, setViewMode] = useState('gallery'); // 'gallery' | 'table'
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [failedMediaIds, setFailedMediaIds] = useState(new Set());
  const [refreshKey, setRefreshKey] = useState(0);
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = useCallback(async (pageNum, pageSizeVal) => {
    const params = new URLSearchParams(filters);
    params.append('page', pageNum);
    params.append('page_size', pageSizeVal);

    try {
      const res = await authFetch(`${API_URL}/api/auth/media/moderation/?${params}`);
      if (!res.ok) {
        logger.error('[Moderation] Fetch failed with status:', res.status);
        setMedia([]);
        setTotalCount(0);
        setTotalPages(0);
        return;
      }
      const data = await res.json();
      // Support both paginated response and plain array
      const results = Array.isArray(data) ? data : (data.results || []);
      const count = data.count !== undefined ? data.count : results.length;
      setMedia(results);
      setFailedMediaIds(new Set());
      setTotalCount(count);
      setTotalPages(Math.ceil(count / pageSizeVal) || 1);
      // Reset selection on fresh load
      setSelectedIds([]);
      setSelectAll(false);
    } catch (err) {
      logger.error('[Moderation] Fetch error:', err);
      setMedia([]);
      setTotalCount(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  }, [filters, API_URL]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Fetch whenever page, pageSize, or the fetchMedia function changes
  useEffect(() => {
    setLoading(true);
    fetchMedia(page, pageSize);
  }, [page, pageSize, fetchMedia, refreshKey]);

  const handleApprove = (id) => {
    if (!window.confirm(t('admin_approve_confirm'))) return;
    authFetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'approved' })
    }).then(res => {
      if (!res.ok) logger.error('[Moderation] Approve failed for ID:', id);
      if (res.ok) {
        fetchMedia(page, pageSize);
      }
    });
  };

  const handleReject = (id) => {
    if (!window.confirm(t('admin_reject_confirm'))) return;
    authFetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'rejected' })
    }).then(res => {
      if (!res.ok) logger.error('[Moderation] Reject failed for ID:', id);
      if (res.ok) {
        fetchMedia(page, pageSize);
      }
    });
  };

  const handleDelete = (id) => {
    if (!window.confirm(t('admin_delete_confirm'))) return;
    authFetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'DELETE'
    }).then(res => {
      if (res.ok) {
        fetchMedia(page, pageSize);
      } else {
        logger.error('[Moderation] Delete failed for ID:', id);
      }
    });
  };

  // Bulk selection handlers
  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedIds([]);
    } else {
      setSelectedIds(media.map(item => item.id));
    }
    setSelectAll(!selectAll);
  };

  const toggleSelectItem = (id) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id);
      } else {
        return [...prev, id];
      }
    });
  };

  // Update selectAll state when individual selections change
  useEffect(() => {
    if (selectedIds.length === media.length && media.length > 0) {
      setSelectAll(true);
    } else {
      setSelectAll(false);
    }
  }, [selectedIds, media]);

  const handleBulkAction = (action) => {
    if (selectedIds.length === 0) return;
    const confirmMsg = t(`admin_bulk_${action}_confirm`, { count: selectedIds.length });
    if (!window.confirm(confirmMsg)) return;
    authFetch(`${API_URL}/api/auth/media/moderation/bulk/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        media_ids: selectedIds,
        action: action
      })
    }).then(res => {
      if (res.ok) {
        setPage(1);
        setRefreshKey(prev => prev + 1);
      } else {
        logger.error('[Moderation] Bulk action failed');
      }
    });
  };

  const handleDetectFaces = () => {
    if (selectedIds.length === 0) return;

    // Filter to images only (videos are ignored by the backend)
    const imageMedia = media.filter(item => selectedIds.includes(item.id) && item.media_type === 'image');
    const skippedCount = selectedIds.length - imageMedia.length;

    if (imageMedia.length === 0) {
      alert(t('admin_detect_faces_no_images'));
      return;
    }

    const confirmMsg = skippedCount > 0
      ? t('admin_detect_faces_confirm_with_skipped', { approved: imageMedia.length, skipped: skippedCount })
      : t('admin_detect_faces_confirm', { count: imageMedia.length });

    if (!window.confirm(confirmMsg)) return;

    authFetch(`${API_URL}/api/auth/media/moderation/detect-faces/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        media_ids: imageMedia.map(m => m.id),
        force: true
      })
    })
      .then(res => res.json())
      .then(data => {
        alert(data.message || t('admin_detect_faces_success'));
        setPage(1);
        setRefreshKey(prev => prev + 1);
      })
      .catch(err => {
        logger.error('[Moderation] Detect faces failed:', err);
        alert(t('admin_detect_faces_error'));
      });
  };

  const getStatusBadge = (status) => {
    const badges = { pending: 'status-pending', approved: 'status-approved', rejected: 'status-rejected' };
    const icons = { pending: '⏳', approved: '✅', rejected: '❌' };
    return <span className={`status-badge ${badges[status]}`}>{icons[status]} {t(status)}</span>;
  };

  if (loading) {
    return (
      <div className="text-center py-10">
        <span className="text-4xl heartDecoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">{t('admin_moderation_loading')}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">{t('admin_moderation_title')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">{t('admin_moderation_subtitle')}</p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

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

        <div className="mb-6 flex gap-4 flex-wrap items-center">
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className="wedding-input">
            <option value="">{t('all')}</option>
            <option value="pending">{t('pending')}</option>
            <option value="approved">{t('approved')}</option>
            <option value="rejected">{t('rejected')}</option>
          </select>
          <select value={filters.media_type} onChange={(e) => setFilters({ ...filters, media_type: e.target.value })} className="wedding-input">
            <option value="">{t('admin_filter_all_types')}</option>
            <option value="image">{t('admin_filter_photos')}</option>
            <option value="video">{t('admin_filter_videos')}</option>
          </select>
          {selectedIds.length > 0 && (
            <div className="flex gap-2 ml-auto overflow-x-auto whitespace-nowrap max-w-full">
              <button onClick={() => handleBulkAction('approve')} className="bg-green-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-600 flex-shrink-0">
                {t('admin_bulk_approve', { count: selectedIds.length })}
              </button>
              <button onClick={() => handleBulkAction('reject')} className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600 flex-shrink-0">
                {t('admin_bulk_reject', { count: selectedIds.length })}
              </button>
              <button onClick={() => handleBulkAction('delete')} className="bg-gray-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-600 flex-shrink-0">
                {t('admin_bulk_delete', { count: selectedIds.length })}
              </button>
              <button
                onClick={handleDetectFaces}
                className="bg-purple-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-600 flex-shrink-0"
              >
                {t('admin_detect_faces')} ({selectedIds.length})
              </button>
            </div>
          )}
        </div>

        {/* Pagination controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <label htmlFor="pageSizeSelect" className="text-sm text-gray-600">
              {t('items_per_page')}
            </label>
            <select
              id="pageSizeSelect"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="wedding-input w-20"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => setPage(1)}
              disabled={page === 1}
              className="wedding-btn text-xs px-1 py-0.5 sm:px-2 sm:py-1 disabled:opacity-50"
            >
              ««
            </button>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="wedding-btn text-xs px-1 py-0.5 sm:px-2 sm:py-1 disabled:opacity-50"
            >
              ‹
            </button>
            <span className="text-sm text-gray-700">
              {t('page_x_of_y', { current: page, total: totalPages })}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="wedding-btn text-xs px-1 py-0.5 sm:px-2 sm:py-1 disabled:opacity-50"
            >
              ›
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages}
              className="wedding-btn text-xs px-1 py-0.5 sm:px-2 sm:py-1 disabled:opacity-50"
            >
              »»
            </button>
          </div>
        </div>

        {viewMode === 'table' ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-pink-200">
                  <th className="text-left py-3 text-pink-600">
                    <input type="checkbox" checked={selectAll} onChange={toggleSelectAll} />
                  </th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_preview')}</th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_user')}</th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_caption')}</th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_date')}</th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_status')}</th>
                  <th className="text-left py-3 text-pink-600">{t('admin_mod_col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {media.map((item) => (
                  <tr key={item.id} className="border-b border-pink-100 hover:bg-pink-50">
                    <td className="py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelectItem(item.id)}
                      />
                    </td>
                    <td className="py-3">
                      <Link to={`/media/${item.id}`} state={{ media: item }}>
                        {failedMediaIds.has(item.id) ? (
                          <div className="w-16 h-16 bg-gray-100 rounded-lg border-2 border-pink-200 flex items-center justify-center text-gray-400 text-xs">
                            {t('file_unavailable')}
                          </div>
                        ) : (
                          item.media_type === 'video' ? (
                            <video
                              src={`${API_URL}${item.file_url}`}
                              className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200"
                              muted
                              preload="metadata"
                              onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                            />
                          ) : (
                            <img
                              src={`${API_URL}${item.file_url}`}
                              alt="preview"
                              className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200"
                              onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                            />
                          )
                        )}
                      </Link>
                    </td>
                    <td className="py-3 text-gray-700">{item.user_email || t('anonymous')}</td>
                    <td className="py-3 text-gray-600 text-sm">{item.caption || '-'}</td>
                    <td className="py-3 text-gray-600 text-sm">{new Date(item.uploaded_at).toLocaleDateString()}</td>
                    <td className="py-3">{getStatusBadge(item.status)}</td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        {item.status === 'pending' && (
                          <>
                            <button onClick={() => handleApprove(item.id)} className="bg-green-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-green-600">{t('admin_approve')}</button>
                            <button onClick={() => handleReject(item.id)} className="bg-red-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-red-600">{t('admin_reject')}</button>
                          </>
                        )}
                        <button onClick={() => handleDelete(item.id)} className="bg-gray-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-gray-600">{t('admin_delete')}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <>
            {/* Select All for gallery mode */}
            <div className="flex items-center mb-2">
              <input
                type="checkbox"
                checked={selectAll}
                onChange={toggleSelectAll}
                className="w-4 h-4 text-wedding-600 border-gray-300 rounded focus:ring-wedding-500"
              />
              <span className="ml-2 text-sm text-gray-600">{t('select_all')}</span>
            </div>
            {/* Gallery grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {media.map(item => (
                <div
                  key={item.id}
                  className="bg-white rounded-lg shadow overflow-hidden relative cursor-pointer"
                  onClick={() => toggleSelectItem(item.id)}
                >
                  {/* Checkbox for bulk selection */}
                  <div className="absolute top-2 left-2 z-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelectItem(item.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 text-wedding-600 border-gray-300 rounded focus:ring-wedding-500"
                    />
                  </div>
                  {/* Media preview */}
                  <div className="aspect-w-1 aspect-h-1 bg-gray-200">
                    {failedMediaIds.has(item.id) ? (
                      <div className="w-full aspect-square bg-gray-100 flex items-center justify-center text-gray-400">
                        <div className="text-center">
                          <span className="text-4xl">🖼️‍🗑️</span>
                          <p className="text-xs mt-1">{t('file_unavailable')}</p>
                        </div>
                      </div>
                    ) : (
                      item.file_url ? (
                        item.media_type === 'video' ? (
                          <video
                            src={`${API_URL}${item.file_url}`}
                            className="object-cover w-full h-full"
                            muted
                            preload="metadata"
                            onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                          />
                        ) : (
                          <img
                            src={`${API_URL}${item.file_url}`}
                            alt={item.caption || 'Media'}
                            className="object-cover w-full h-full"
                            onError={() => setFailedMediaIds(prev => new Set(prev).add(item.id))}
                          />
                        )
                      ) : (
                        <div className="flex items-center justify-center h-full text-gray-400">📁</div>
                      )
                    )}
                  </div>
                  {/* Info and actions */}
                  <div className="p-3">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.caption || t('no_caption')}
                    </p>
                    <p className="text-xs text-gray-500">
                      {item.username || item.user__username || t('unknown')}
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      {getStatusBadge(item.status)}
                      <div className="flex space-x-1">
                        {item.status !== 'approved' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleApprove(item.id);
                            }}
                            className="text-green-600 hover:text-green-800 text-xs px-2 py-1 rounded border border-green-300"
                            title={t('approve')}
                          >
                            ✅
                          </button>
                        )}
                        {item.status !== 'rejected' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReject(item.id);
                            }}
                            className="text-yellow-600 hover:text-yellow-800 text-xs px-2 py-1 rounded border border-yellow-300"
                            title={t('reject')}
                          >
                            ❌
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(item.id);
                          }}
                          className="text-red-600 hover:text-red-800 text-xs px-2 py-1 rounded border border-red-300"
                          title={t('delete')}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AdminModeration;
