import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const Settings = () => {
  const { t } = useTranslation();
  const [settings, setSettings] = useState({
    site_name: '', maintenance_mode: false, allow_registrations: true,
    max_upload_size_mb: 50, require_approval: true, default_language: 'it',
    frontend_url: '',
    // Google OAuth
    google_client_id: '', google_client_secret: '',
    // Facebook OAuth
    facebook_app_id: '', facebook_app_secret: '',
    // Instagram OAuth
    instagram_app_id: '', instagram_app_secret: '',
    // Nextcloud
    nextcloud_url: '', nextcloud_username: '', nextcloud_password: '', nextcloud_folder: '',
    // SMTP
    email_host: '', email_port: 587, email_use_tls: true, email_host_user: '', email_host_password: '', default_from_email: ''
  });
  const [success, setSuccess] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    authFetch(`${API_URL}/api/auth/admin/settings/`)
      .then(res => res.json())
      .then(data => setSettings(data))
      .catch(err => logger.error('[Settings] Settings fetch error:', err));
  }, [API_URL]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/settings/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) setSuccess(t('admin_settings_saved'));
    } catch (err) {
      logger.error('[Settings] Settings save error:', err);
      logger.error('[Settings] Settings data:', settings);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">{t('admin_settings_title')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">{t('admin_settings_subtitle')}</p>
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">{success}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('admin_settings_site_name')}</label>
            <input type="text" value={settings.site_name} onChange={(e) => setSettings({...settings, site_name: e.target.value})} className="wedding-input w-full" />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('admin_settings_frontend_url')}</label>
            <input type="url" value={settings.frontend_url} onChange={(e) => setSettings({...settings, frontend_url: e.target.value})} className="wedding-input w-full" placeholder={t('admin_settings_frontend_url_placeholder')} />
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.maintenance_mode} onChange={(e) => setSettings({...settings, maintenance_mode: e.target.checked})} className="mr-2" />
              {t('admin_settings_maintenance_mode')}
            </label>
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.allow_registrations} onChange={(e) => setSettings({...settings, allow_registrations: e.target.checked})} className="mr-2" />
              {t('admin_settings_allow_registrations')}
            </label>
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('admin_settings_max_upload_size')}</label>
            <input type="number" value={settings.max_upload_size_mb} onChange={(e) => setSettings({...settings, max_upload_size_mb: parseInt(e.target.value)})} className="wedding-input w-full" />
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.require_approval} onChange={(e) => setSettings({...settings, require_approval: e.target.checked})} className="mr-2" />
              {t('admin_settings_require_approval')}
            </label>
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">{t('admin_settings_default_language')}</label>
            <select value={settings.default_language} onChange={(e) => setSettings({...settings, default_language: e.target.value})} className="wedding-input w-full">
              <option value="it">{t('Italiano')}</option>
              <option value="ko">{t('한국어')}</option>
              <option value="en">{t('English')}</option>
            </select>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">{t('Google OAuth')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('Client ID')}</label>
                <input type="text" name="google_client_id" value={settings.google_client_id} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Client Secret')}</label>
                <input type="password" name="google_client_secret" value={settings.google_client_secret} onChange={handleChange} className="wedding-input w-full" />
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">{t('Facebook OAuth')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('App ID')}</label>
                <input type="text" name="facebook_app_id" value={settings.facebook_app_id} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('App Secret')}</label>
                <input type="password" name="facebook_app_secret" value={settings.facebook_app_secret} onChange={handleChange} className="wedding-input w-full" />
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">{t('Instagram OAuth')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('App ID')}</label>
                <input type="text" name="instagram_app_id" value={settings.instagram_app_id} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('App Secret')}</label>
                <input type="password" name="instagram_app_secret" value={settings.instagram_app_secret} onChange={handleChange} className="wedding-input w-full" />
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">{t('Nextcloud')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('URL')}</label>
                <input type="text" name="nextcloud_url" value={settings.nextcloud_url} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Username')}</label>
                <input type="text" name="nextcloud_username" value={settings.nextcloud_username} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Password')}</label>
                <input type="password" name="nextcloud_password" value={settings.nextcloud_password} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Folder')}</label>
                <input type="text" name="nextcloud_folder" value={settings.nextcloud_folder} onChange={handleChange} className="wedding-input w-full" />
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">{t('SMTP')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('Host')}</label>
                <input type="text" name="email_host" value={settings.email_host} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Port')}</label>
                <input type="number" name="email_port" value={settings.email_port} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="flex items-center">
                  <input type="checkbox" name="email_use_tls" checked={settings.email_use_tls} onChange={handleChange} className="mr-2" />
                  {t('Use TLS')}
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Username')}</label>
                <input type="text" name="email_host_user" value={settings.email_host_user} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('Password')}</label>
                <input type="password" name="email_host_password" value={settings.email_host_password} onChange={handleChange} className="wedding-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('From Email')}</label>
                <input type="email" name="default_from_email" value={settings.default_from_email} onChange={handleChange} className="wedding-input w-full" />
              </div>
            </div>
          </div>

          <button type="submit" className="wedding-btn w-full">{t('admin_save_settings')}</button>
        </form>
      </div>
    </div>
  );
};

export default Settings;
