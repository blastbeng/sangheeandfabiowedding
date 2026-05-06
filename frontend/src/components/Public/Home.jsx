import { Link } from 'react-router-dom';
import coupleImage from '../../static/images/SangHeeAndFabio.png';

const Home = () => {
  return (
    <div className="min-h-screen">
      {/* Hero Section with Large Couple Photo */}
      <div className="wedding-card mx-4 mt-8 p-8 md:p-16 text-center ribbon wedding-glow relative overflow-hidden">
        {/* Decorative Background Elements */}
        <div className="absolute top-0 left-0 text-6xl opacity-20 floating-heart">💕</div>
        <div className="absolute top-0 right-0 text-6xl opacity-20 floating-heart">🌸</div>
        <div className="absolute bottom-0 left-0 text-6xl opacity-20 floating-heart">✨</div>
        <div className="absolute bottom-0 right-0 text-6xl opacity-20 floating-heart">💕</div>

        {/* Large Couple Photo - Centerpiece */}
        <div className="mb-10 flex justify-center relative">
          <div className="photo-frame rounded-full overflow-hidden w-72 h-72 md:w-96 md:h-96 shadow-2xl border-8 border-yellow-400 floating-heart wedding-glow">
            <img
              src={coupleImage}
              alt="Sang Hee & Fabio - The Happy Couple"
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/400x400?text=Sang+Hee+%26+Fabio';
              }}
            />
          </div>
          {/* Decorative ribbon overlay */}
          <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-pink-400 to-yellow-400 text-white px-8 py-2 rounded-full text-sm font-bold shadow-lg">
            💍 Forever & Always 💍
          </div>
        </div>

        {/* Main Title with Couple Names */}
        <h1 className="text-5xl md:text-8xl wedding-title mb-6 sparkle">
          💕 Sang Hee & Fabio 💕
        </h1>
        
        {/* Romantic Tagline */}
        <p className="text-2xl md:text-3xl text-pink-600 mb-8 italic font-playfair wedding-gradient-text">
          🌸 Two Hearts, One Beautiful Journey 🌸
        </p>

        {/* Welcome Message - More Casual */}
        <div className="max-w-4xl mx-auto mb-10">
          <p className="text-xl text-gray-700 leading-relaxed mb-6">
            💌 Hey there, lovely people!
          </p>
          <p className="text-lg text-gray-700 leading-relaxed mb-6">
            Welcome to our wedding memory collection – a special place where love stories come alive 
            and precious moments are treasured forever. We're absolutely over the moon to celebrate 
            this magical chapter of our lives with each and every one of you!
          </p>
          <p className="text-lg text-gray-700 leading-relaxed mb-6">
            This beautiful space is dedicated to capturing every smile, every tear of joy, 
            every dance under the stars, and every heartfelt moment from our special day. 
            Your unique perspective makes our story complete.
          </p>
          <p className="text-lg text-gray-700 leading-relaxed">
            📸 Share your photos and videos, browse through memories captured by our loved ones, 
            and help us create a timeless treasure trove that we'll cherish for generations to come. 
            Every snapshot you share adds more sparkle and love to our forever! ✨💝
          </p>
        </div>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        {/* CTA Buttons */}
        <div className="flex gap-6 justify-center flex-wrap mt-10">
          <Link to="/gallery" className="wedding-btn text-lg px-8 py-4">
            📸 Explore Our Gallery
          </Link>
          <Link to="/upload" className="wedding-btn text-lg px-8 py-4">
            📤 Share Your Memory
          </Link>
        </div>
      </div>

      {/* Love Story Section */}
      <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto p-4 mt-12">
        <div className="wedding-card p-10 text-center wedding-glow floating-heart">
          <span className="text-7xl block mb-6">💑</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-4 wedding-title">Two Hearts, One Love</h3>
          <p className="text-gray-600 leading-relaxed text-lg">
            Sang Hee and Fabio's love story began with a single magical moment. 
            From that day forward, their hearts have beaten as one. 
            Now, they invite you to be part of their forever. 
            Every love story is beautiful, but theirs is their favorite. 💕
          </p>
        </div>
        
        <div className="wedding-card p-10 text-center wedding-glow floating-heart">
          <span className="text-7xl block mb-6">📸</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-4 wedding-title">Capture the Magic</h3>
          <p className="text-gray-600 leading-relaxed text-lg">
            Those candid smiles, the happy tears, the dancing feet under the stars – 
            every moment you capture becomes a precious treasure we'll hold dear forever. 
            Your lens sees the beauty that ours might miss. 
            Help us remember every detail of this perfect day! ✨
          </p>
        </div>
        
        <div className="wedding-card p-10 text-center wedding-glow floating-heart">
          <span className="text-7xl block mb-6">💝</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-4 wedding-title">Share the Love</h3>
          <p className="text-gray-600 leading-relaxed text-lg">
            Upload your photos and videos to our shared gallery. 
            Together, we'll weave a beautiful tapestry of memories that will 
            warm our hearts for generations to come. 
            Your contribution makes our love story complete! 🌸
          </p>
        </div>
      </div>

      {/* Romantic Quote Section */}
      <div className="wedding-card mx-4 mt-12 p-12 text-center ribbon wedding-glow">
        <div className="max-w-4xl mx-auto">
          <span className="text-6xl mb-6 inline-block floating-heart">💕</span>
          <blockquote className="text-3xl md:text-4xl wedding-gradient-text font-playfair italic mb-6 leading-relaxed">
            "In all the world, there is no heart for me like yours. 
            In all the world, there is no love for you like mine."
          </blockquote>
          <p className="text-gray-600 text-xl">— Maya Angelou</p>
          <div className="floral-divider mt-8">✿ ─────── ✿ ─────── ✿</div>
          <p className="text-lg text-pink-600 italic mt-6">
            🌹 Just like Sang Hee & Fabio found their perfect match 🌹
          </p>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="max-w-6xl mx-auto p-4 mt-12">
        <h2 className="text-5xl wedding-title text-center mb-4">🌹 Share Your Memories 🌹</h2>
        <p className="text-center text-gray-600 mb-10 text-lg italic">
          It's easy as 1-2-3-4 to be part of our special day!
        </p>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-5xl mb-4 floating-heart">1️⃣</div>
            <h4 className="font-bold text-pink-600 mb-3 text-xl">Sign Up</h4>
            <p className="text-gray-600">Create your account in seconds</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-5xl mb-4 floating-heart">2️⃣</div>
            <h4 className="font-bold text-pink-600 mb-3 text-xl">Upload</h4>
            <p className="text-gray-600">Share your photos and videos</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-5xl mb-4 floating-heart">3️⃣</div>
            <h4 className="font-bold text-pink-600 mb-3 text-xl">Add Caption</h4>
            <p className="text-gray-600">Tell us about the moment</p>
          </div>
          <div className="wedding-card p-8 text-center wedding-glow">
            <div className="text-5xl mb-4 floating-heart">4️⃣</div>
            <h4 className="font-bold text-pink-600 mb-3 text-xl">Enjoy</h4>
            <p className="text-gray-600">Relive the magic forever</p>
          </div>
        </div>
      </div>

      {/* Final CTA Section */}
      <div className="text-center p-8 mt-12 mb-8">
        <div className="wedding-card mx-auto max-w-3xl p-12 ribbon wedding-glow">
          <span className="text-7xl mb-6 inline-block floating-heart">🌸</span>
          <p className="text-4xl wedding-title mb-6">Ready to Be Part of the Magic?</p>
          <p className="text-gray-600 mb-8 text-xl leading-relaxed">
            Your memories are the missing pieces to our perfect day. 
            Every photo you share, every video you upload, adds more love and joy 
            to our collection. Don't keep those beautiful moments hidden – 
            share the love and let's create something unforgettable together! 💕
          </p>
          <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
          <Link to="/register" className="wedding-btn text-xl px-10 py-4 inline-block mt-8">
            ✨ Yes, Count Me In!
          </Link>
        </div>
      </div>

      {/* Footer Message */}
      <div className="text-center pb-12">
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
        <p className="text-gray-500 italic text-lg">
          💕 Made with endless love by Sang Hee & Fabio 💕
        </p>
        <p className="text-gray-400 text-sm mt-2">
          Forever & Always | Our Wedding Memory Project © 2024
        </p>
        <div className="mt-4 text-3xl">
          <span className="inline-block floating-heart mx-2">💕</span>
          <span className="inline-block floating-heart mx-2">🌸</span>
          <span className="inline-block floating-heart mx-2">✨</span>
          <span className="inline-block floating-heart mx-2">💝</span>
          <span className="inline-block floating-heart mx-2">🌹</span>
        </div>
      </div>
    </div>
  );
};

export default Home;
