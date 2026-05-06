import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const AdminDashboard = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_URL}/api/auth/admin/dashboard/`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => res.json())
      .then(data => { setStats(data); setLoading(false); })
      .catch(err => { console.error('Dashboard fetch error:', err); setLoading(false); });
  }, [API_URL]);

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">Loading admin dashboard...</p>
      </div>
    );
  }

  const statCards = [
    { title: 'Total Users', value: stats?.total_users || 0, icon: '👥', color: 'from-blue-400 to-blue-500' },
    { title: 'Administrators', value: stats?.total_admins || 0, icon: '⭐', color: 'from-yellow-400 to-yellow-500' },
    { title: 'Total Media', value: stats?.total_media || 0, icon: '📸', color: 'from-pink-400 to-pink-500' },
    { title: 'Pending', value: stats?.pending_media || 0, icon: '⏳', color: 'from-orange-400 to-orange-500' },
    { title: 'Approved', value: stats?.approved_media || 0, icon: '✅', color: 'from-green-400 to-green-500' },
    { title: 'Rejected', value: stats?.rejected_media || 0, icon: '❌', color: 'from-red-400 to-red-500' },
  ];

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8 mb-8">
        <h1 className="text-4xl wedding-title text-center mb-2">⭐ Administration Panel</h1>
        <p className="text-center text-gray-600 italic">Manage users, content, and settings 💕</p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {statCards.map((stat, index) => (
          <div key={index} className={`wedding-card p-4 text-center wedding-glow bg-gradient-to-br ${stat.color}`}>
            <span className="text-3xl block mb-2">{stat.icon}</span>
            <p className="text-white font-bold text-2xl">{stat.value}</p>
            <p className="text-white text-sm opacity-90">{stat.title}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-4 gap-6">
        <Link to="/admin/users" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">👥</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">User Management</h3>
          <p className="text-gray-600 text-sm">Create, edit, delete users</p>
        </Link>
        
        <Link to="/admin/moderation" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">📸</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Media Moderation</h3>
          <p className="text-gray-600 text-sm">Approve or reject uploads</p>
        </Link>
        
        <Link to="/admin/settings" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">⚙️</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">App Settings</h3>
          <p className="text-gray-600 text-sm">Configure webapp options</p>
        </Link>
        
        <Link to="/" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">🏠</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Back to Home</h3>
          <p className="text-gray-600 text-sm">Return to main site</p>
        </Link>
      </div>
    </div>
  );
};

export default AdminDashboard;
