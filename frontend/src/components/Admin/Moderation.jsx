import { useEffect, useState } from 'react';

const AdminModeration = () => {
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: 'pending', media_type: '' });
  const [selectedIds, setSelectedIds] = useState([]);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [bulkAction, setBulkAction] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchMedia = () => {
    const params = new URLSearchParams(filters);
    fetch(`${API_URL}/api/auth/media/moderation/?${params}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => res.json())
      .then(data => {
        setMedia(data);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMedia();
  }, [filters]);

  const handleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === media.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(media.map(m => m.id));
    }
  };

  const handleBulkAction = (action) => {
    if (selectedIds.length === 0) return;

    if (action === 'reject') {
      setBulkAction('reject');
      setShowRejectModal(true);
      return;
    }

    fetch(`${API_URL}/api/auth/media/moderation/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({ media_ids: selectedIds, action })
    })
      .then(res => {
        if (res.ok) {
          fetchMedia();
          setSelectedIds([]);
        }
      });
  };

  const handleSingleAction = (id, action) => {
    if (action === 'reject') {
      setBulkAction('reject');
      setSelectedIds([id]);
      setShowRejectModal(true);
      return;
    }

    fetch(`${API_URL}/api/auth/media/moderation/${id}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({ action })
    })
      .then(res => {
        if (res.ok) fetchMedia();
      });
  };

  const confirmReject = () => {
    fetch(`${API_URL}/api/auth/media/moderation/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: JSON.stringify({ 
        media_ids: selectedIds, 
        action: 'reject',
        rejection_reason: rejectionReason 
      })
    })
      .then(res => {
        if (res.ok) {
          fetchMedia();
          setSelectedIds([]);
          setRejectionReason('');
          setShowRejectModal(false);
        }
      });
  };

  if (loading) return <div className="text-center p-8">Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Content Moderation</h2>

      {/* Filters */}
      <div className="bg-white p-4 rounded shadow mb-6">
        <div className="flex gap-4 flex-wrap">
          <select 
            value={filters.status} 
            onChange={e => setFilters({...filters, status: e.target.value})}
            className="border p-2 rounded"
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </select>
          <select 
            value={filters.media_type} 
            onChange={e => setFilters({...filters, media_type: e.target.value})}
            className="border p-2 rounded"
          >
            <option value="">All Types</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-100 p-4 rounded mb-6">
          <span className="font-semibold">{selectedIds.length} selected</span>
          <button 
            onClick={() => handleBulkAction('approve')}
            className="ml-4 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Approve Selected
          </button>
          <button 
            onClick={() => handleBulkAction('reject')}
            className="ml-2 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Reject Selected
          </button>
        </div>
      )}

      {/* Media Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {media.map(item => (
          <div key={item.id} className="bg-white p-4 rounded shadow relative">
            <input 
              type="checkbox" 
              checked={selectedIds.includes(item.id)}
              onChange={() => handleSelect(item.id)}
              className="absolute top-2 right-2 w-4 h-4"
            />
            <div className="mb-2">
              {item.media_type === 'video' ? (
                <video src={`${API_URL}${item.file_url}`} controls className="w-full h-48 object-cover" />
              ) : (
                <img src={`${API_URL}${item.file_url}`} alt={item.caption} className="w-full h-48 object-cover" />
              )}
            </div>
            <div className="flex items-center gap-2 mb-2">
              <img 
                src={item.user?.profile_picture || 'https://i.imgur.com/V4RclNb.png'} 
                className="w-6 h-6 rounded-full"
              />
              <span className="text-sm font-semibold">{item.username || 'Anonymous'}</span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{item.caption}</p>
            <div className={`text-sm font-semibold mb-2 ${
              item.status === 'approved' ? 'text-green-600' :
              item.status === 'rejected' ? 'text-red-600' : 'text-yellow-600'
            }`}>
              Status: {item.status.toUpperCase()}
            </div>
            {item.status === 'pending' && (
              <div className="flex gap-2">
                <button 
                  onClick={() => handleSingleAction(item.id, 'approve')}
                  className="flex-1 bg-green-600 text-white px-2 py-1 rounded text-sm hover:bg-green-700"
                >
                  Approve
                </button>
                <button 
                  onClick={() => handleSingleAction(item.id, 'reject')}
                  className="flex-1 bg-red-600 text-white px-2 py-1 rounded text-sm hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded shadow-md max-w-md w-full">
            <h3 className="text-lg font-bold mb-4">Rejection Reason</h3>
            <textarea 
              value={rejectionReason}
              onChange={e => setRejectionReason(e.target.value)}
              className="w-full border p-2 rounded mb-4"
              rows="4"
              placeholder="Enter reason for rejection..."
            />
            <div className="flex gap-2">
              <button 
                onClick={confirmReject}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Confirm Reject
              </button>
              <button 
                onClick={() => { setShowRejectModal(false); setRejectionReason(''); setSelectedIds([]); }}
                className="flex-1 bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminModeration;
