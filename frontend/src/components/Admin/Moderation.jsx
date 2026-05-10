import { useEffect, useState } from 'react';
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
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = () => {
    const params = new URLSearchParams(filters);
    authFetch(`${API_URL}/api/auth/media/moderation/?${params}`)
      .then(res => {
        if (!res.ok) {
          logger.error('[Moderation] Fetch failed with status:', res.status);
        }
        return res.json();
      })
      .then(data => {
        setMedia(data);
        setLoading(false);
        // Reset selection when data changes
        setSelectedIds([]);
        setSelectAll(false);
      })
      .catch(err => {
        logger.error('[Moderation] Fetch error:', err);
        setLoading(false);
      });
  };

  useEffect(() => { fetchMedia(); }, [filters]);

  const handleApprove = (id) => {
    authFetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'approved' })
    }).then(res => {
      if (!res.ok) logger.error('[Moderation] Approve failed for ID:', id);
      if (res.ok) fetchMedia();
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
      if (res.ok) fetchMedia();
    });
  };

  const handleDelete = (id) => {
    if (!window.confirm(t('admin_delete_confirm'))) return;
    authFetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'DELETE'
    }).then(res => {
      if (res.ok) {
        fetchMedia();
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
    authFetch(`${API_URL}/api/auth/media/moderation/bulk/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        media_ids: selectedIds,
        action: action
      })
    }).then(res => {
      if (res.ok) {
        fetchMedia();
      } else {
        logger.error('[Moderation] Bulk action failed');
      }
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
        <span className="text-4xl heart-decoration inline-block">💝</span>
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
            <div className="flex gap-2 ml-auto">
              <button onClick={() => handleBulkAction('approve')} className="bg-green-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-600">
                {t('admin_bulk_approve', { count: selectedIds.length })}
              </button>
              <button onClick={() => handleBulkAction('reject')} className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600">
                {t('admin_bulk_reject', { count: selectedIds.length })}
              </button>
              <button onClick={() => handleBulkAction('delete')} className="bg-gray-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-600">
                {t('admin_bulk_delete', { count: selectedIds.length })}
              </button>
            </div>
          )}
        </div>

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
                      <img src={`${API_URL}${item.file_url}`} alt="preview" className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200 hover:opacity-80 transition" />
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
      </div>
    </div>
  );
};

export default AdminModeration;
