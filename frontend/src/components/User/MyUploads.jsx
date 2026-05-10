import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const MyUploads = () => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedIds, setSelectedIds] = useState([]);
  const [message, setMessage] = useState(null); // { type: 'success'|'error', text: '' }
  const API_URL = import.meta.env.VITE_API_URL;

  const refreshUploads = () => setRefreshTrigger(prev => prev + 1);

  // Auto-dismiss messages after 4 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

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
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: 'success', text: data.message || t('my_uploads_bulk_delete_success') });
        setSelectedIds([]);
        refreshUploads();
      } else {
        setMessage({ type: 'error', text: data.error || t('my_uploads_bulk_delete_error') });
      }
    } catch (err) {
      logger.error('[MyUploads] Bulk delete failed:', err);
      setMessage({ type: 'error', text: t('my_uploads_bulk_delete_error') });
    }
  };

  useEffect(() => {
    authFetch(`${API_URL}/api/auth/media/my-uploads/`)
      .then(res => res.json())
      .then(data => { setUploads(data); setLoading(false); })
      .catch(err => { 
        logger.error('[MyUploads] Failed to fetch uploads:', err); 
        setLoading(false); 
      });
  }, [refreshTrigger]);

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

        {uploads.length === 0 ? (
          <div className="text-center py-10">
            <span className="text-6xl floating-heart inline-block">📸</span>
            <p className="mt-4 text-gray-600 text-lg">{t('my_uploads_no_uploads')}</p>
            <p className="text-gray-500 text-sm">{t('my_uploads_share_first')}</p>
            <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
            <Link to="/upload" className="wedding-btn inline-block mt-4">{t('my_uploads_upload_now')}</Link>
          </div>
        ) : (
          <>
            {/* Bulk delete button */}
            {selectedIds.length > 0 && (
              <div className="mb-4 flex justify-end">
                <button
                  onClick={handleBulkDelete}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm"
                >
                  {t('my_uploads_delete_selected', { count: selectedIds.length })}
                </button>
              </div>
            )}

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
                          <img src={`${API_URL}${upload.file_url}`} alt={t('my_uploads_preview_alt')} className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200" />
                        ) : <span className="text-2xl">🎬</span>}
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
          </>
        )}
      </div>
    </div>
  );
};

export default MyUploads;
