import { useEffect, useState } from 'react';

const Gallery = () => {
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/auth/media/')
      .then(res => res.json())
      .then(res => res.json())
      .then(data => {
        setMedia(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="text-center p-8">Loading gallery...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {media.map(item => (
        <div key={item.id} className="bg-white p-2 rounded shadow">
          {item.media_type === 'video' ? (
            <video src={item.file_url} controls className="w-full" />
          ) : (
            <img src={item.file_url} alt={item.caption} className="w-full" />
          )}
          <div className="flex items-center mt-2">
            <img 
              src={item.user?.profile_picture || 'https://i.imgur.com/V4RclNb.png'} 
              alt={item.user?.username || 'User'} 
              className="w-8 h-8 rounded-full mr-2 object-cover"
            />
            <span className="text-sm font-semibold">{item.user?.username || 'Anonymous'}</span>
          </div>
          <p className="text-sm text-gray-600">{item.caption}</p>
        </div>
      ))}
      {media.length === 0 && <p className="col-span-3 text-center text-gray-500">No content yet.</p>}
        </div>
      ))}
    </div>
  );
};
export default Gallery;
