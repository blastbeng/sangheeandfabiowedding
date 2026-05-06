import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div className="min-h-screen">
      <div className="wedding-card mx-4 mt-8 p-12 text-center ribbon">
        <h1 className="text-6xl wedding-title mb-4">💕 You're Invited to Our Special Day! 💕</h1>
        <p className="text-xl text-gray-600 mb-6 italic">
          Welcome to our little corner of love and memories 🌸
        </p>
        <p className="text-gray-700 mb-8 max-w-2xl mx-auto leading-relaxed">
          We're absolutely over the moon to celebrate our wedding with you! 
          This is where all the magic happens – share your precious photos and videos, 
          browse through beautiful moments captured by our loved ones, 
          and help us create a treasure trove of memories we'll cherish forever. 
          Every snapshot you share adds more sparkle to our special day! ✨💝
        </p>
        <div className="floral-divider">✿ ─────── ✿ ─────── ✿</div>
        <div className="flex gap-4 justify-center flex-wrap mt-8">
          <Link to="/gallery" className="wedding-btn">
            📸 Peek at Our Gallery
          </Link>
          <Link to="/upload" className="wedding-btn">
            📤 Share Your Love
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto p-4 mt-8">
        <div className="wedding-card p-6 text-center wedding-glow">
          <span className="text-5xl block mb-4 floating-heart">📸</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Capture the Magic</h3>
          <p className="text-gray-600 text-sm">
            Snap those precious moments throughout our magical day – every click is a memory forever!
          </p>
        </div>
        <div className="wedding-card p-6 text-center wedding-glow">
          <span className="text-5xl block mb-4 floating-heart">💝</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Share the Love</h3>
          <p className="text-gray-600 text-sm">
            Upload your favorite moments to our shared gallery – let's build our memory book together!
          </p>
        </div>
        <div className="wedding-card p-6 text-center wedding-glow">
          <span className="text-5xl block mb-4 floating-heart">✨</span>
          <h3 className="text-xl font-bold text-pink-600 mb-2">Treasure Forever</h3>
          <p className="text-gray-600 text-sm">
            Relive the joy, laughter, and love whenever your heart desires – these memories are eternal!
          </p>
        </div>
      </div>

      <div className="text-center p-8 mt-8">
        <p className="text-2xl wedding-title mb-4">🌹 Ready to Join the Celebration? 🌹</p>
        <p className="text-gray-600 mb-6">Create your account in a flash and start sharing!</p>
        <Link to="/register" className="wedding-btn text-lg">
          ✨ Yes, Count Me In!
        </Link>
      </div>
    </div>
  );
};

export default Home;
