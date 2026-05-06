import { useTranslation } from 'react-i18next';
import { setLanguage } from '../i18n';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'it', label: 'IT', flag: '🇮🇹' },
    { code: 'ko', label: 'KO', flag: '🇰🇷' },
    { code: 'en', label: 'EN', flag: '🇬🇧' },
  ];

  const changeLanguage = (lng) => {
    setLanguage(lng);
  };

  return (
    <div className="flex gap-2 items-center">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => changeLanguage(lang.code)}
          className={`px-3 py-1 rounded-lg text-sm font-semibold transition-all border-2 ${
            i18n.language === lang.code
              ? 'border-pink-500 bg-pink-500 text-white'
              : 'border-pink-300 bg-white text-gray-600 hover:bg-pink-50 hover:text-pink-600'
          }`}
        >
          {lang.flag} {lang.label}
        </button>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
