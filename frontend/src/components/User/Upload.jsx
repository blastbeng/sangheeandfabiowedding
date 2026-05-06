import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const Upload = () => {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [captions, setCaptions] = useState({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL;

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
    selectedFiles.forEach(file => {
      setCaptions(prev => ({ ...prev, [file.name]: '' }));
    });
  };

  const handleCaptionChange = (fileName, value) => {
    setCaptions(prev => ({ ...prev, [fileName]: value }));
  };

  const removeFile = (fileName) => {
    setFiles(prev => prev.filter(f => f.name !== fileName));
    setCaptions(prev => {
      const newCaptions = { ...prev };
      delete newCaptions[fileName];
      return newCaptions;
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append('files', file);
      formData.append(`captions[${index}]`, captions[file.name] || '');
      formData.append(`media_types[${index}]`, file.type.startsWith('video') ? 'video' : 'image');
    });

    try {
      const res = await fetch(`${API_URL}/api/auth/media/upload/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(`${files.length} file(s) queued for processing`);
        setTimeout(() => navigate('/my-uploads'), 2000);
      } else {
        setError(data.error || 'Upload failed');
      }
    } catch (err) {
      setError('An error occurred during upload');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">📤 Share Your Memories</h2>
        <p className="text-center text-gray-600 mb-6 italic">Upload your beautiful photos and videos from our special day 🌹</p>

        {error && <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4">💔 {error}</div>}
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">✅ {success}</div>}

        <div className="mb-6">
          <label className="block text-gray-700 text-sm font-bold mb-2">📸 Select Photos & Videos</label>
          <input type="file" multiple accept="image/*,video/*" onChange={handleFileSelect} className="wedding-input w-full py-4" />
          <p className="text-sm text-gray-500 mt-2">✨ Supported: JPG, PNG, MP4, MOV</p>
        </div>

        {files.length > 0 && (
          <>
            <div className="mb-6">
              <h3 className="text-lg font-bold mb-3 text-pink-600">📁 Files Selected ({files.length})</h3>
              {files.map((file, index) => (
                <div key={index} className="bg-pink-50 p-3 rounded-xl mb-2 flex justify-between items-center">
                  <span className="text-sm">📄 {file.name}</span>
                  <button onClick={() => removeFile(file.name)} className="text-red-500 hover:text-red-700 text-sm">❌ Remove</button>
                </div>
              ))}
            </div>
            <div className="mb-6">
              <h3 className="text-lg font-bold mb-3 text-pink-600">✏️ Add Captions (Optional)</h3>
              {files.map((file, index) => (
                <div key={index} className="mb-3">
                  <label className="block text-gray-700 text-xs font-bold mb-1">📝 {file.name}</label>
                  <input type="text" value={captions[file.name] || ''} onChange={(e) => handleCaptionChange(file.name, e.target.value)} className="wedding-input w-full text-sm" placeholder="Add a sweet memory..." />
                </div>
              ))}
            </div>
          </>
        )}

        <button onClick={handleUpload} disabled={files.length === 0 || uploading} className="wedding-btn w-full disabled:opacity-50 disabled:cursor-not-allowed">
          {uploading ? '⏳ Uploading...' : '💝 Upload Memories'}
        </button>
      </div>
    </div>
  );
};

export default Upload;
