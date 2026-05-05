import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Upload = () => {
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('caption', caption);
    formData.append('media_type', file.type.startsWith('video') ? 'video' : 'image');

    try {
      const res = await fetch('http://localhost:8032/api/auth/media/upload/', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` },
        body: formData
      });
      if (res.ok) navigate('/gallery');
    } catch (err) { console.error(err); }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto bg-white p-6 rounded shadow">
      <input type="file" onChange={e => setFile(e.target.files[0])} required className="mb-4" />
      <input type="text" placeholder="Caption" value={caption} onChange={e => setCaption(e.target.value)} className="w-full border p-2 mb-4" />
      <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Upload</button>
    </form>
  );
};
export default Upload;
