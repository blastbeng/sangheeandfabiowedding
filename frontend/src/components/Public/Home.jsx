import { Link } from 'react-router-dom';
import coupleImage from '../static/images/SangHeeAndFabio.png';

const Home = () => {
  return (
    <div className="min-h-screen">
      {/* Hero Section with Couple Photo */}
      <div className="wedding-card mx-4 mt-8 p-8 md:p-12 text-center ribbon wedding-glow">
        {/* Couple Photo */}
        <div className="mb-8 flex justify-center">
          <div className="photo-frame rounded-full overflow-hidden w-64 h-64 md:w-80 md:h-80 shadow-2xl border-4 border-yellow-400">
            <img
              src={coupleImage}
              alt="Sang Hee & Fabio - The Happy Couple"
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Main Title */}
        <h1 className="text-5xl md:text-7xl wedding-title mb-4 sparkle">
          💕 Sang Hee & Fabio 💕
        </h1>
        
        {/* Wedding Date Tagline */}
        <p className="text-2xl text-pink-600 mb-6 italic font-playfair">
          🌸 Together Forever Starts Here 🌸
        </p>

        {/* Welcome Message */}
        <div className="max-w-3xl mx-auto mb-8">
          <p className="text-lg text-gray-700 leading-relaxed mb-4">
            Welcome to our wedding memory collection, where love stories come to life! 
            We're absolutely thrilled to celebrate this magical chapter of our lives with you.
          </p>
          <p className="text-lg text-gray-700 leading-relaxed mb-4">
            This special space is dedicated to capturing every precious moment, 
            every joyful laugh, and every tear of happiness from our beautiful day.
          </p>
          <p className="text-lg text-gray-700 leading-relaxed">
            Your photos and videos are the missing pieces to our memory puzzle. 
            Share your perspective of our love story, and let's create something 
            truly unforgettable together! ✨💝
          </p>
        </div>

        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center flex-wrap mt-8">
          <Link to="/gallery" className="wedding-btn text-lg">
            📸 Explore Our Gallery
          </Link>
          <Link to="/upload" className="wedding-btn text-lg">
            📤 Share Your Memory
          </Link>
        </div>
      </div>

      {/* Love Story Section */}
      <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto p-4 mt-8">
        <div className="wedding-card p-8 text-center wedding-glow floating-heart">
          <span className="text-6xl block mb-4">💑</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-3 wedding-title">Two Hearts, One Love</h3>
          <p className="text-gray-600 leading-relaxed">
            Sang Hee and Fabio's journey began with a single moment, 
            and now they're inviting you to be part of their forever. 
            Every love story is beautiful, but theirs is their favorite.
          </p>
        </div>
        
        <div className="wedding-card p-8 text-center wedding-glow floating-heart">
          <span className="text-6xl block mb-4">📸</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-3 wedding-title">Capture the Magic</h3>
          <p className="text-gray-600 leading-relaxed">
            Those candid smiles, the happy tears, the dancing feet – 
            every moment you capture becomes a treasure we'll hold dear. 
            Your lens sees what ours might miss!
          </p>
        </div>
        
        <div className="wedding-card p-8 text-center wedding-glow floating-heart">
          <span className="text-6xl block mb-4">💝</span>
          <h3 className="text-2xl font-bold text-pink-600 mb-3 wedding-title">Share the Love</h3>
          <p className="text-gray-600 leading-relaxed">
            Upload your photos and videos to our shared gallery. 
            Together, we'll weave a tapestry of memories that will 
            warm our hearts for generations to come.
          </p>
        </div>
      </div>

      {/* Romantic Quote Section */}
      <div className="wedding-card mx-4 mt-8 p-8 text-center ribbon">
        <div className="max-w-4xl mx-auto">
          <span className="text-5xl mb-4 inline-block floating-heart">💕</span>
          <blockquote className="text-2xl md:text-3xl wedding-gradient-text font-playfair italic mb-4">
            "In all the world, there is no heart for me like yours. 
            In all the world, there is no love for you like mine."
          </blockquote>
          <p className="text-gray-600 text-lg">— Maya Angelou</p>
          <div className="floral-divider mt-6">✿ ─────── ✿ ─────── ✿</div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="max-w-6xl mx-auto p-4 mt-8">
        <h2 className="text-4xl wedding-title text-center mb-8">🌹 How to Share Your Memories 🌹</h2>
        <div className="grid md:grid-cols-4 gap-4">
          <div className="wedding-card p-6 text-center">
            <div className="text-4xl mb-3">1️⃣</div>
            <h4 className="font-bold text-pink-600 mb-2">Sign Up</h4>
            <p className="text-sm text-gray-600">Create your account in seconds</p>
          </div>
          <div className="wedding-card p-6 text-center">
            <div className="text-4xl mb-3">2️⃣</div>
            <h4 className="font-bold text-pink-600 mb-2">Upload</h4>
            <p className="text-sm text-gray-600">Share your photos & videos</p>
          </div>
          <div className="wedding-card p-6 text-center">
            <div className="text-4xl mb-3">3️⃣</div>
            <h4 className="font-bold text-pink-600 mb-2">Add Caption</h4>
            <p className="text-sm text-gray-600">Tell us about the moment</p>
          </div>
          <div className="wedding-card p-6 text-center">
            <div className="text-4xl mb-3">4️⃣</div>
            <h4 className="font-bold text-pink-600 mb-2">Enjoy</h4>
            <p className="text-sm text-gray-600">Relive the magic forever</p>
          </div>
        </div>
      </div>

      {/* Final CTA Section */}
      <div className="text-center p-8 mt-8 mb-8">
        <div className="wedding-card mx-auto max-w-2xl p-8 ribbon wedding-glow">
          <span className="text-6xl mb-4 inline-block floating-heart">🌸</span>
          <p className="text-3xl wedding-title mb-4">Ready to Join the Celebration?</p>
          <p className="text-gray-600 mb-6 text-lg">
            Your memories are the missing pieces to our perfect day. 
            Don't keep them hidden – share the love!
          </p>
          <Link to="/register" className="wedding-btn text-xl">
            ✨ Yes, Count Me In!
          </Link>
        </div>
      </div>

      {/* Footer Message */}
      <div className="text-center pb-8">
        <p className="text-gray-500 italic">
          Made with endless love by Sang Hee & Fabio 💕 | Forever & Always
        </p>
      </div>
    </div>
  );
};

export default Home;
