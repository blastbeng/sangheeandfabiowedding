import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const Settings = () => {
  const { t } = useTranslation();
  const [settings, setSettings] = useState({
    site_name: '', maintenance_mode: false, allow_registrations: true,
    max_upload_size_mb: 50, require_approval: true, default_language: 'it'
  });
  const [success, setSuccess] = useState('');
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_URL}/api/auth/admin/settings/`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => res.json())
      .then(data => setSettings(data))
      .catch(err => console.error('Settings fetch error:', err));
  }, [API_URL]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/api/auth/admin/settings/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify(settings)
      });
      if (res.ok) setSuccess('Settings saved successfully! ✅');
    } catch (err) {
      console.error('Settings save error:', err);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">⚙️ App Settings</h2>
        <p className="text-center text-gray-600 mb-6 italic">Configure your webapp 💕</p>
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">{success}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Site Name</label>
            <input type="text" value={settings.site_name} onChange={(e) => setSettings({...settings, site_name: e.target.value})} className="wedding-input w-full" />
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.maintenance_mode} onChange={(e) => setSettings({...settings, maintenance_mode: e.target.checked})} className="mr-2" />
              Maintenance Mode
            </label>
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.allow_registrations} onChange={(e) => setSettings({...settings, allow_registrations: e.target.checked})} className="mr-2" />
              Allow New Registrations
            </label>
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Max Upload Size (MB)</label>
            <input type="number" value={settings.max_upload_size_mb} onChange={(e) => setSettings({...settings, max_upload_size_mb: parseInt(e.target.value)})} className="wedding-input w-full" />
          </div>
          <div className="mb-4">
            <label className="flex items-center">
              <input type="checkbox" checked={settings.require_approval} onChange={(e) => setSettings({...settings, require_approval: e.target.checked})} className="mr-2" />
              Require Media Approval
            </label>
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Default Language</label>
            <select value={settings.default_language} onChange={(e) => setSettings({...settings, default_language: e.target.value})} className="wedding-input w-full">
              <option value="it">🇮🇹 Italiano</option>
              <option value="ko">🇰🇷 한국어</option>
              <option value="en">🇬🇧 English</option>
            </select>
          </div>
          <button type="submit" className="wedding-btn w-full">💾 Save Settings</button>
        </form>
      </div>
    </div>
  );
};

export default Settings;
