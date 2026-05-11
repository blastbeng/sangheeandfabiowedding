import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';

const CookieConsent = () => {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    // Check if user has already consented
    const localConsent = localStorage.getItem('cookieConsent');
    if (localConsent) {
      setConsentGiven(true);
      return;
    }

    // If authenticated, check server for consent
    const token = localStorage.getItem('accessToken');
    if (token) {
      fetchServerConsent();
    } else {
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
    localStorage.setItem('cookieConsent', JSON.stringify(prefs));
    syncWithServer(prefs);
    setConsentGiven(true);
    setVisible(false);
  };

  const handleNecessaryOnly = () => {
    const prefs = { analytics: false, marketing: false, necessary: true };
    localStorage.setItem('cookieConsent', JSON.stringify(prefs));
    syncWithServer(prefs);
    setConsentGiven(true);
    setVisible(false);
  };

  if (!visible || consentGiven) return null;

  return (
    <div className="bg-white border-t-2 border-pink-200 shadow-lg p-4 md:p-6">
      <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-gray-700 text-sm md:text-base flex-1">
          🍪 {t('cookie_consent_message')}
        </p>
        <div className="flex gap-2">
          <button
            onClick={handleNecessaryOnly}
            className="px-4 py-2 text-sm border-2 border-gray-300 rounded-full text-gray-600 hover:bg-gray-100 transition"
          >
            {t('cookie_necessary_only')}
          </button>
          <button
            onClick={handleAcceptAll}
            className="wedding-btn text-sm px-4 py-2"
          >
            {t('cookie_accept_all')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CookieConsent;
