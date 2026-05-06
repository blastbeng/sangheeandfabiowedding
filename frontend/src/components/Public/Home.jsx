import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import coupleImage from '../../static/images/SangHeeAndFabio.png';

const Home = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="wedding-card mx-4 mt-8 p-8 md:p-16 text-center ribbon wedding-glow">
        {/* Couple Photo */}
        <div className="mb-10 flex justify-center">
          <div className="photo-frame rounded-full overflow-hidden w-64 h-64 md:w-80 md:h-80 shadow-xl border-6 border-yellow-400">
            <img
              src={coupleImage}
              alt="Sang Hee & Fabio"
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/400x400?text=Sang+Hee+%26+Fabio';
              }}
            />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-5xl md:text-7xl wedding-title mb-4">
          Sang Hee &amp; Fabio
        </h1>
        
        {/* Tagline */}
        <p className="text-xl md:text-2xl text-pink-600 mb-8 italic font-playfair">
          2024 — Costigliole d'Asti
        </p>

        {/* Welcome Message - Using i18n */}
        <div className="max-w-3xl mx-auto mb-10">
          <p className="text-lg text-gray-700 leading-relaxed mb-4">
            {t('welcome_message_1')}
          </p>
          <p className="text-lg text-gray-700 leading-relaxed">
            {t('welcome_message_2')}
          </p>
        </div>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        {/* CTA Buttons */}
        <div className="flex gap-6 justify-center flex-wrap mt-10">
          <Link to="/gallery" className="wedding-btn text-lg px-8 py-4">
            {t('Gallery')}
          </Link>
          <Link to="/upload" className="wedding-btn text-lg px-8 py-4">
            {t('Upload')}
          </Link>
        </div>
      </div>

      {/* How It Works - Simplified */}
      <div className="max-w-6xl mx-auto p-4 mt-12">
        <h2 className="text-4xl wedding-title text-center mb-8">{t('how_it_works')}</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-4xl mb-4 text-pink-600 font-bold">1</div>
            <h4 className="font-bold text-gray-800 mb-2 text-lg">{t('step1_title')}</h4>
            <p className="text-gray-600 text-sm">{t('step1_desc')}</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-4xl mb-4 text-pink-600 font-bold">2</div>
            <h4 className="font-bold text-gray-800 mb-2 text-lg">{t('step2_title')}</h4>
            <p className="text-gray-600 text-sm">{t('step2_desc')}</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-4xl mb-4 text-pink-600 font-bold">3</div>
            <h4 className="font-bold text-gray-800 mb-2 text-lg">{t('step3_title')}</h4>
            <p className="text-gray-600 text-sm">{t('step3_desc')}</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-4xl mb-4 text-pink-600 font-bold">4</div>
            <h4 className="font-bold text-gray-800 mb-2 text-lg">{t('step4_title')}</h4>
            <p className="text-gray-600 text-sm">{t('step4_desc')}</p>
          </div>
        </div>
      </div>

      {/* Final CTA */}
      <div className="text-center p-8 mt-12 mb-8">
        <div className="wedding-card mx-auto max-w-2xl p-10 ribbon wedding-glow">
          <p className="text-2xl wedding-title mb-4">{t('join_us_title')}</p>
          <p className="text-gray-600 mb-6 leading-relaxed">
            {t('join_us_message')}
          </p>
          <Link to="/register" className="wedding-btn text-lg px-8 py-3">
            {t('Create Account')}
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center pb-12">
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
        <p className="text-gray-500 italic text-sm">
          Sang Hee &amp; Fabio — 2024
        </p>
      </div>
    </div>
  );
};

export default Home;
