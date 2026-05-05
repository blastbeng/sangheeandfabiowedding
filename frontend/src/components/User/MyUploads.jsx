import { useEffect, useState } from 'react';

const MyUploads = () => {
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_URL}/api/auth/media/my-uploads/`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => res.json())
      .then(data => {
        setUploads(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const getStatusColor = (status) => {
    switch(status) {
      case 'approved': return 'text-green-600';
      case 'pending': return 'text-yellow-600';
      case 'rejected': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  if (loading) return <div className="text-center p-8">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">My Uploads</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {uploads.map(item => (
          <div key={item.id} className="bg-white p-2 rounded shadow">
            {item.media_type === 'video' ? (
              <video src={item.file_url} controls className="w-full" />
            ) : (
              <img src={item.file_url} alt={item.caption} className="w-full" />
            )}
            <div className={`mt-2 font-semibold ${getStatusColor(item.status)}`}>
              Status: {item.status.toUpperCase()}
            </div>
            {item.status === 'rejected' && item.rejection_reason && (
              <p className="text-sm text-red-500 mt-1">Reason: {item.rejection_reason}</p>
            )}
            <p className="text-sm text-gray-600">{item.caption}</p>
            <p className="text-xs text-gray-400">{new Date(item.uploaded_at).toLocaleDateString()}</p>
          </div>
        ))}
      </div>
      {uploads.length === 0 && <p className="text-center text-gray-500">No uploads yet.</p>}
    </div>
  );
};

export default MyUploads;
