import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

const PendingApproval = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="wedding-card p-8 max-w-md w-full text-center">
        <span className="text-5xl inline-block">💔</span>
        <h2 className="text-2xl wedding-title mt-4">{t('pending_approval_title')}</h2>
        <p className="text-gray-600 mt-2">{t('pending_approval_message')}</p>
        <button
          onClick={() => navigate('/')}
          className="wedding-btn inline-block mt-6"
        >
          {t('go_to_home')}
        </button>
      </div>
    </div>
  );
};

export default PendingApproval;
