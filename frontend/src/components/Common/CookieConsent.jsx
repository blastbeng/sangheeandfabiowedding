import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';

const CookieConsent = () => {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [preferences, setPreferences] = useState({
    analytics: false,
    marketing: false,
    necessary: true,
  });
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    // Check if user has already consented
    const localConsent = localStorage.getItem('cookieConsent');
    if (localConsent) {
      try {
        const parsed = JSON.parse(localConsent);
        setPreferences(parsed);
        setConsentGiven(true);
      } catch {
        // Invalid stored data, show banner
        setVisible(true);
      }
      return;
    }

    // If authenticated, check server for consent
    const token = localStorage.getItem('accessToken');
    if (token) {
      fetchServerConsent();
    } else {
      // Show banner for anonymous users
      setVisible(true);
    }
  }, []);

  const fetchServerConsent = async () => {
    try {
      const res = await authFetch(`${API_URL}/api/auth/cookie-consent/`);
      if (res.ok) {
        const data = await res.json();
        const prefs = {
          analytics: data.analytics,
          marketing: data.marketing,
          necessary: data.necessary,
        };
        setPreferences(prefs);
        localStorage.setItem('cookieConsent', JSON.stringify(prefs));
        setConsentGiven(true);
      } else {
        setVisible(true);
      }
    } catch {
      setVisible(true);
    }
  };

  const syncWithServer = async (prefs) => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;
    try {
      await authFetch(`${API_URL}/api/auth/cookie-consent/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
      });
    } catch {
      // Silently fail - local storage is the fallback
    }
  };

  const handleAcceptAll = () => {
    const prefs = { analytics: true, marketing: true, necessary: true };
    setPreferences(prefs);
    localStorage.setItem('cookieConsent', JSON.stringify(prefs));
    syncWithServer(prefs);
    setConsentGiven(true);
    setVisible(false);
  };

  const handleRejectAll = () => {
    const prefs = { analytics: false, marketing: false, necessary: true };
    setPreferences(prefs);
    localStorage.setItem('cookieConsent', JSON.stringify(prefs));
    syncWithServer(prefs);
    setConsentGiven(true);
    setVisible(false);
  };

  const handleSavePreferences = () => {
    localStorage.setItem('cookieConsent', JSON.stringify(preferences));
    syncWithServer(preferences);
    setConsentGiven(true);
    setVisible(false);
    setShowSettings(false);
  };

  if (!visible && !consentGiven) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      {/* Full consent banner (initial or when reopening settings) */}
      {visible && (
        <div className="bg-white border-t-2 border-pink-200 shadow-lg p-4 md:p-6">
          <div className="max-w-4xl mx-auto">
            {!showSettings ? (
              <>
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                  <div className="flex-1">
                    <p className="text-gray-700 text-sm md:text-base">
                      🍪 {t('cookie_consent_message')}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={handleRejectAll}
                      className="px-4 py-2 text-sm border-2 border-gray-300 rounded-full text-gray-600 hover:bg-gray-100 transition"
                    >
                      {t('cookie_reject_all')}
                    </button>
                    <button
                      onClick={() => setShowSettings(true)}
                      className="px-4 py-2 text-sm border-2 border-pink-300 rounded-full text-pink-600 hover:bg-pink-50 transition"
                    >
                      {t('cookie_customize')}
                    </button>
                    <button
                      onClick={handleAcceptAll}
                      className="wedding-btn text-sm px-4 py-2"
                    >
                      {t('cookie_accept_all')}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <h3 className="text-lg font-bold text-pink-600 mb-3">🍪 {t('cookie_settings_title')}</h3>
                <div className="space-y-3 mb-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-700">{t('cookie_necessary')}</p>
                      <p className="text-xs text-gray-500">{t('cookie_necessary_desc')}</p>
                    </div>
                    <input type="checkbox" checked disabled className="h-5 w-5 text-pink-600" />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-700">{t('cookie_analytics')}</p>
                      <p className="text-xs text-gray-500">{t('cookie_analytics_desc')}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.analytics}
                      onChange={(e) => setPreferences({ ...preferences, analytics: e.target.checked })}
                      className="h-5 w-5 text-pink-600 rounded"
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-700">{t('cookie_marketing')}</p>
                      <p className="text-xs text-gray-500">{t('cookie_marketing_desc')}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.marketing}
                      onChange={(e) => setPreferences({ ...preferences, marketing: e.target.checked })}
                      className="h-5 w-5 text-pink-600 rounded"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleSavePreferences}
                    className="wedding-btn text-sm px-6 py-2"
                  >
                    💾 {t('cookie_save_preferences')}
                  </button>
                  <button
                    onClick={() => setShowSettings(false)}
                    className="px-4 py-2 text-sm border-2 border-gray-300 rounded-full text-gray-600 hover:bg-gray-100 transition"
                  >
                    {t('admin_cancel')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Persistent thin bar – always visible after consent */}
      {!visible && consentGiven && (
        <div className="bg-white/95 backdrop-blur-sm border-t-2 border-pink-200 shadow-md py-2 px-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <p className="text-xs md:text-sm text-gray-600">
              🍪 {t('cookie_bar_message')}
            </p>
            <button
              onClick={() => { setVisible(true); setShowSettings(true); }}
              className="text-xs md:text-sm text-pink-600 hover:text-pink-800 underline font-medium"
            >
              {t('cookie_manage_preferences')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CookieConsent;
