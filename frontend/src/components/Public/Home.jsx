import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div className="min-h-screen">
      <div className="wedding-card mx-4 mt-8 p-12 text-center">
        <h1 className="text-6xl wedding-title mb-4">💕 You're Invited! 💕</h1>
        <p className="text-xl text-gray-600 mb-6 italic">
          Welcome to our wedding memory collection 🌸
        </p>
        <p className="text-gray-700 mb-8 max-w-2xl mx-auto">
          We're so excited to celebrate our special day with you! 
          Share your photos and videos, and let's create beautiful memories together. 
          Every moment captured is a treasure we'll cherish forever. 💝
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link to="/gallery" className="wedding-btn">
            📸 View Gallery
          </Link>
          <Link to="/upload" className="wedding-btn">
            📤 Share Memory
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto p-4 mt-8">
        <div className="wedding-card p-6 text-center">
          <span className="text-5xl block mb-4">📸</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Capture Moments</h3>
          <p className="text-gray-600 text-sm">
            Take photos and videos throughout our special day
          </p>
        </div>
        <div className="wedding-card p-6 text-center">
          <span className="text-5xl block mb-4">💝</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Share Love</h3>
          <p className="text-gray-600 text-sm">
            Upload your memories to our shared gallery
          </p>
        </div>
        <div className="wedding-card p-6 text-center">
          <span className="text-5xl block mb-4">✨</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Relive Forever</h3>
          <p className="text-gray-600 text-sm">
            Look back on our beautiful celebration anytime
          </p>
        </div>
      </div>

      <div className="text-center p-8 mt-8">
        <p className="text-2xl wedding-title mb-4">🌹 Join the Celebration 🌹</p>
        <Link to="/register" className="wedding-btn text-lg">
          ✨ Create Your Account
        </Link>
      </div>
    </div>
  );
};

export default Home;
