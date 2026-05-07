import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const AdminModeration = () => {
  const { t } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: 'pending', media_type: '' });
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = () => {
    const params = new URLSearchParams(filters);
    fetch(`${API_URL}/api/auth/media/moderation/?${params}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => {
        if (!res.ok) {
          console.error('[Moderation] Fetch failed with status:', res.status);
        }
        return res.json();
      })
      .then(data => { setMedia(data); setLoading(false); })
      .catch(err => { 
        console.error('[Moderation] Fetch error:', err); 
        setLoading(false); 
      });
  };

  useEffect(() => { fetchMedia(); }, [filters]);

  const handleApprove = (id) => {
    fetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({ status: 'approved' })
    }).then(res => { 
      if (!res.ok) console.error('[Moderation] Approve failed for ID:', id);
      if (res.ok) fetchMedia(); 
    });
  };

  const handleReject = (id) => {
    setSelectedId(id);
    setShowRejectModal(true);
  };

  const confirmReject = () => {
    fetch(`${API_URL}/api/auth/media/moderation/${selectedId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({ status: 'rejected', rejection_reason: rejectionReason })
    }).then(res => {
      if (!res.ok) console.error('[Moderation] Reject failed for ID:', selectedId);
      if (res.ok) {
        fetchMedia();
        setRejectionReason('');
        setShowRejectModal(false);
        setSelectedId(null);
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
        <p className="mt-4 text-gray-600">Loading submissions...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">⭐ Moderation Center</h2>
        <p className="text-center text-gray-600 mb-6 italic">Review and approve beautiful memories 💕</p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        <div className="mb-6 flex gap-4 flex-wrap">
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className="wedding-input">
            <option value="pending">⏳ Pending</option>
            <option value="approved">✅ Approved</option>
            <option value="rejected">❌ Rejected</option>
          </select>
          <select value={filters.media_type} onChange={(e) => setFilters({ ...filters, media_type: e.target.value })} className="wedding-input">
            <option value="">🎬 All Types</option>
            <option value="image">📸 Photos</option>
            <option value="video">🎥 Videos</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-pink-200">
                <th className="text-left py-3 text-pink-600">🖼️</th>
                <th className="text-left py-3 text-pink-600">👤 User</th>
                <th className="text-left py-3 text-pink-600">📝 Caption</th>
                <th className="text-left py-3 text-pink-600">📅 Date</th>
                <th className="text-left py-3 text-pink-600">💫 Status</th>
                <th className="text-left py-3 text-pink-600">⚡ Actions</th>
              </tr>
            </thead>
            <tbody>
              {media.map((item) => (
                <tr key={item.id} className="border-b border-pink-100 hover:bg-pink-50">
                  <td className="py-3">
                    <img src={`${API_URL}${item.file_url}`} alt="preview" className="w-16 h-16 object-cover rounded-lg border-2 border-pink-200" />
                  </td>
                  <td className="py-3 text-gray-700">{item.user_email || 'Anonymous'}</td>
                  <td className="py-3 text-gray-600 text-sm">{item.caption || '-'}</td>
                  <td className="py-3 text-gray-600 text-sm">{new Date(item.uploaded_at).toLocaleDateString()}</td>
                  <td className="py-3">{getStatusBadge(item.status)}</td>
                  <td className="py-3">
                    {item.status === 'pending' && (
                      <div className="flex gap-2">
                        <button onClick={() => handleApprove(item.id)} className="bg-green-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-green-600">✅ Approve</button>
                        <button onClick={() => handleReject(item.id)} className="bg-red-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-red-600">❌ Reject</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="wedding-card p-6 max-w-md w-full">
            <h3 className="text-lg font-bold mb-4 text-pink-600">💔 Rejection Reason</h3>
            <textarea value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} className="wedding-input w-full mb-4" rows="4" placeholder="Enter reason for rejection..." />
            <div className="flex gap-2">
              <button onClick={confirmReject} className="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">Confirm Reject</button>
              <button onClick={() => { setShowRejectModal(false); setRejectionReason(''); setSelectedId(null); }} className="flex-1 bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminModeration;
