import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import scheduleImage from '../../static/images/SangHee_and_Fabio_schedule.png';
import ceremonyLocationImage from '../../static/images/ComeRaggiungerci-cerimonia.png';

const Events = () => {
  const { t, i18n } = useTranslation();
  const [currentLang, setCurrentLang] = useState(i18n.language || 'it');

  useEffect(() => {
    const handleLanguageChange = () => {
      setCurrentLang(i18n.language || 'it');
    };
    
    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  // Event data extracted from PSD invitation files
  const events = [
    {
      id: 1,
      type: 'ceremony',
      title: {
        it: 'Cerimonia Civile',
        ko: '시민 결혼식',
        en: 'Civil Ceremony'
      },
      subtitle: {
        it: 'Presso la Sala Consiglio del Comune di Costigliore d\'Asti',
        ko: '코스틸리올레 다스티 시의회 회의실에서',
        en: 'At the Council Hall of Costigliore d\'Asti Municipality'
      },
      icon: '💒',
      description: {
        it: 'Unisciti a noi per scambiare i nostri voti in una cerimonia intima e significativa nel cuore di Costigliore d\'Asti.',
        ko: '코스틸리올레 다스티 중심부에서 진행되는 친밀하고 의미 있는 예식에서 저희의 서약을 함께 나누어 주세요.',
        en: 'Join us as we exchange our vows in an intimate and meaningful ceremony in the heart of Costigliore d\'Asti.'
      },
      locationImage: ceremonyLocationImage,
      details: [
        { label: { it: 'Luogo', ko: '장소', en: 'Venue' }, value: 'Sala Consiglio, Comune di Costigliore d\'Asti' },
        { label: { it: 'Indirizzo', ko: '주소', en: 'Address' }, value: 'Piazza Roma, Costigliore d\'Asti, AT, Italia' },
        { label: { it: 'Data', ko: '날짜', en: 'Date' }, value: '2024' },
      ],
      color: 'from-pink-400 to-rose-400',
      psdFile: 'Cerimonia presso in Sala Consglio del Comune di Costigliore d\'Asti.psd'
    },
    {
      id: 2,
      type: 'reception',
      title: {
        it: 'Ricevimento di Nozze',
        ko: '결혼 피로연',
        en: 'Wedding Reception'
      },
      subtitle: {
        it: 'Festa di Nostro Matrimonio - Ore 12:00',
        ko: '우리 결혼 축하 연회 - 오후 12 시',
        en: 'Our Wedding Celebration - 12:00 PM'
      },
      icon: '🥂',
      description: {
        it: 'Dopo la cerimonia, celebreremo il nostro amore con una festa indimenticabile piena di gioia, danza e buon cibo!',
        ko: '예식 후, 기쁨과 춤, 그리고 맛있는 음식이 가득한 잊을 수 없는 파티로 저희의 사랑을 축하합니다!',
        en: 'After the ceremony, we\'ll celebrate our love with an unforgettable party full of joy, dance, and delicious food!'
      },
      details: [
        { label: { it: 'Luogo', ko: '장소', en: 'Venue' }, value: 'PODERE LA PIAZZA' },
        { label: { it: 'Indirizzo', ko: '주소', en: 'Address' }, value: 'Strada Piazza, 4, 14055 Costigliole d\'Asti AT, Italia' },
        { label: { it: 'Orario', ko: '시간', en: 'Time' }, value: '12:00 - Pranzo / Lunch' },
        { label: { it: 'Dress Code', ko: '드레스 코드', en: 'Dress Code' }, value: 'Elegante / Elegant' },
      ],
      color: 'from-yellow-400 to-amber-400',
      psdFile: 'Invito per la festa di nostro matrimonio.psd'
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="wedding-card mx-4 mt-8 p-8 md:p-12 text-center ribbon wedding-glow">
        <span className="text-6xl mb-4 inline-block floating-heart">📅</span>
        <h1 className="text-5xl md:text-7xl wedding-title mb-4 sparkle">
          {t('Our Wedding Events')}
        </h1>
        <p className="text-xl text-gray-600 mb-6 italic">
          {currentLang === 'it' && "Tutti i dettagli del nostro grande giorno"}
          {currentLang === 'ko' && "저희의 특별한 날에 대한 모든 세부 사항"}
          {currentLang === 'en' && "All the details of our big day"}
        </p>
        <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed mb-8">
          {currentLang === 'it' && "Siamo così entusiasti di condividere questi momenti speciali con voi! Ecco tutti i dettagli su dove e quando celebreremo il nostro amore."}
          {currentLang === 'ko' && "이 특별한 순간을 여러분과 함께하게 되어 정말 설레습니다! 저희의 사랑을 축하할 장소와 시간에 대한 모든 세부 사항을 알려드립니다."}
          {currentLang === 'en' && "We're so excited to share these special moments with you! Here are all the details on where and when we'll celebrate our love."}
        </p>
        <div className="bg-gradient-to-r from-pink-50 to-yellow-50 rounded-xl p-6 mt-6 border-2 border-pink-200">
          <p className="text-lg text-gray-700 leading-relaxed italic text-center">
            {currentLang === 'it' && "Siamo felici di condividere il nostro matrimonio con voi! La vera festa inizia quando le risate si accendono e i bicchieri si riempiono di amore e allegria. Averci come nostri ospiti sarà il regalo più grande! Vi aspettiamo per festeggiare insieme!"}
            {currentLang === 'ko' && "저희의 결혼식을 여러분과 함께하게 되어 정말 기쁩니다! 웃음꽃이 피어나고 잔에 사랑과 기쁨이 가득 찰 때 진정한 축제가 시작됩니다. 여러분이 저희의 손님으로 와주시는 것이 가장 큰 선물입니다! 함께 축하해 주시기를 기다리겠습니다!"}
            {currentLang === 'en' && "We are happy to share our wedding with you! The real party begins when laughter ignites and glasses fill with love and joy. Having you as our guests will be the greatest gift! We look forward to celebrating together!"}
          </p>
        </div>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
      </div>

      {/* Schedule Image Section */}
      <div className="max-w-4xl mx-auto mt-8 mb-8 px-4">
        <img 
          src={scheduleImage} 
          alt="SangHee and Fabio Event Schedule" 
          className="w-full h-auto rounded-xl shadow-lg wedding-glow" 
        />
      </div>

      {/* Events Cards */}
      <div className="max-w-6xl mx-auto p-4 mt-8">
        {events.map((event) => (
          <div
            key={event.id}
            className="wedding-card mb-8 overflow-hidden wedding-glow ribbon"
          >
            {/* Event Header with Gradient */}
            <div className={`bg-gradient-to-r ${event.color} p-6 text-white`}>
              <div className="flex items-center justify-center gap-4">
                <span className="text-5xl floating-heart">{event.icon}</span>
                <div className="text-center">
                  <h2 className="text-3xl md:text-4xl font-bold wedding-title text-white drop-shadow-lg">
                    {event.title[currentLang] || event.title.en}
                  </h2>
                  <p className="text-lg opacity-90 italic">
                    {event.subtitle[currentLang] || event.subtitle.en}
                  </p>
                </div>
              </div>
            </div>

            {/* Event Body */}
            <div className="p-8">
              {/* Description */}
              <p className="text-lg text-gray-700 text-center mb-8 leading-relaxed">
                {event.description[currentLang] || event.description.en}
              </p>

              {/* Details Grid */}
              <div className="grid md:grid-cols-3 gap-6 mb-8">
                {event.details.map((detail, index) => (
                  <div
                    key={index}
                    className="bg-pink-50 rounded-xl p-4 text-center border-2 border-pink-200"
                  >
                    <p className="text-sm text-pink-600 font-bold mb-1">
                      {detail.label[currentLang] || detail.label.en}
                    </p>
                    <p className="text-gray-700">{detail.value}</p>
                  </div>
                ))}
              </div>

              {/* Location Image (Conditional) */}
              {event.locationImage && (
                <div className="mb-8">
                  <img 
                    src={event.locationImage} 
                    alt="Ceremony Location and Parking Info" 
                    className="w-full h-auto rounded-xl shadow-lg wedding-glow mb-4" 
                  />
                  <p className="text-sm text-gray-500 text-center italic">
                    {currentLang === 'it' && "Informazioni su parcheggio e ubicación della cerimonia"}
                    {currentLang === 'ko' && "주차장 및 예식장 위치 안내"}
                    {currentLang === 'en' && "Parking and Ceremony Location Info"}
                  </p>
                </div>
              )}

              {/* PSD File Reference */}
              <div className="bg-gradient-to-r from-pink-50 to-yellow-50 rounded-xl p-6 text-center border-2 border-dashed border-pink-300">
                <span className="text-3xl mb-2 inline-block">🎨</span>
                <p className="text-gray-600 font-bold mb-2">
                  {currentLang === 'it' && "Invito Ufficiale"}
                  {currentLang === 'ko' && "공식 초대장"}
                  {currentLang === 'en' && "Official Invitation"}
                </p>
                <p className="text-sm text-gray-500 italic">
                  {event.psdFile}
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  {currentLang === 'it' && "Design originale disponibile su richiesta"}
                  {currentLang === 'ko' && "원본 디자인은 요청 시 제공 가능합니다"}
                  {currentLang === 'en' && "Original design available upon request"}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Couple Info Section */}
      <div className="wedding-card mx-4 mt-8 p-8 text-center ribbon wedding-glow">
        <span className="text-6xl mb-4 inline-block floating-heart">💑</span>
        <h2 className="text-4xl wedding-title mb-4">Sang Hee &amp; Fabio</h2>
        <p className="text-lg text-gray-600 italic mb-6">
          {currentLang === 'it' && "Non vediamo l'ora di celebrare con voi!"}
          {currentLang === 'ko' && "여러분과 함께 이 특별한 날을 축하하기를 기다립니다!"}
          {currentLang === 'en' && "We can't wait to celebrate with you!"}
        </p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link to="/gallery" className="wedding-btn">
            📸 {t('Gallery')}
          </Link>
          <Link to="/upload" className="wedding-btn">
            📤 {t('Share')}
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center pb-12 pt-8">
        <p className="text-gray-500 italic">
          💕 Made with endless love by Sang Hee &amp; Fabio 💕
        </p>
      </div>
    </div>
  );
};

export default Events;
