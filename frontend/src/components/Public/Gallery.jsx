import { useEffect, useState } from 'react';

const Gallery = () => {
  const [media, setMedia] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/auth/media/')
      .then(res => res.json())
      .then(data => setMedia(data));
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {media.map(item => (
        <div key={item.id} className="bg-white p-2 rounded shadow">
          {item.media_type === 'video' ? (
            <video src={item.file} controls className="w-full" />
          ) : (
            <img src={item.file} alt={item.caption} className="w-full" />
          )}
          <p className="text-sm text-gray-600">{item.caption}</p>
        </div>
      ))}
    </div>
  );
};
export default Gallery;
