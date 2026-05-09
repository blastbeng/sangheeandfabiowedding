import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const AdminDashboard = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    authFetch(`${API_URL}/api/auth/admin/dashboard/`)
      .then(res => res.json())
      .then(data => { setStats(data); setLoading(false); })
      .catch(err => { 
        logger.error('[AdminDashboard] Dashboard fetch error:', err); 
        logger.error('[AdminDashboard] API URL:', API_URL);
        logger.error('[AdminDashboard] Token present:', !!localStorage.getItem('accessToken'));
        setLoading(false); 
      });
  }, [API_URL]);

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">{t('admin_loading')}</p>
      </div>
    );
  }

  const statCards = [
    { title: t('stat_total_users'), value: stats?.total_users || 0, icon: '👥', color: 'from-blue-400 to-blue-500' },
    { title: t('stat_administrators'), value: stats?.total_admins || 0, icon: '⭐', color: 'from-yellow-400 to-yellow-500' },
    { title: t('stat_total_media'), value: stats?.total_media || 0, icon: '📸', color: 'from-pink-400 to-pink-500' },
    { title: t('stat_pending'), value: stats?.pending_media || 0, icon: '⏳', color: 'from-orange-400 to-orange-500' },
    { title: t('stat_approved'), value: stats?.approved_media || 0, icon: '✅', color: 'from-green-400 to-green-500' },
    { title: t('stat_rejected'), value: stats?.rejected_media || 0, icon: '❌', color: 'from-red-400 to-red-500' },
  ];

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8 mb-8">
        <h1 className="text-4xl wedding-title text-center mb-2">{t('admin_title')}</h1>
        <p className="text-center text-gray-600 italic">{t('admin_subtitle')}</p>
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
          <h3 className="text-xl font-bold text-pink-600 mb-2">{t('nav_user_management')}</h3>
          <p className="text-gray-600 text-sm">{t('nav_user_management_desc')}</p>
        </Link>
        
        <Link to="/admin/moderation" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">📸</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">{t('nav_media_moderation')}</h3>
          <p className="text-gray-600 text-sm">{t('nav_media_moderation_desc')}</p>
        </Link>
        
        <Link to="/admin/settings" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">⚙️</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">{t('nav_app_settings')}</h3>
          <p className="text-gray-600 text-sm">{t('nav_app_settings_desc')}</p>
        </Link>
        
        <Link to="/" className="wedding-card p-6 text-center wedding-glow hover:scale-105 transition">
          <span className="text-5xl block mb-4">🏠</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">{t('nav_back_home')}</h3>
          <p className="text-gray-600 text-sm">{t('nav_back_home_desc')}</p>
        </Link>
      </div>
    </div>
  );
};

export default AdminDashboard;
