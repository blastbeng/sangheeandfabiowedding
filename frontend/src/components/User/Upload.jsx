import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Upload = () => {
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

  const handleSubmit = async (e) => {
    e.preventDefault();
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
        setSuccess(`${data.uploaded.length} file(s) uploaded successfully`);
        if (data.warning) {
          setError(data.warning + ': ' + (data.errors || []).join(', '));
        }
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
    <div className="max-w-2xl mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-2xl font-bold mb-6">Upload Media</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <input
            type="file"
            onChange={handleFileSelect}
            multiple
            accept="image/*,video/*"
            className="w-full border p-2 rounded"
            disabled={uploading}
          />
          <p className="text-sm text-gray-500 mt-1">Select multiple images or videos</p>
        </div>

        {files.length > 0 && (
          <div className="mb-4 space-y-3">
            {files.map((file) => (
              <div key={file.name} className="border p-3 rounded bg-gray-50">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(file.name)}
                    className="text-red-600 hover:text-red-800 text-sm"
                    disabled={uploading}
                  >
                    Remove
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="Caption (optional)"
                  value={captions[file.name] || ''}
                  onChange={(e) => handleCaptionChange(file.name, e.target.value)}
                  className="w-full border p-2 rounded text-sm"
                  disabled={uploading}
                />
              </div>
            ))}
          </div>
        )}

        <button
          type="submit"
          disabled={files.length === 0 || uploading}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:bg-gray-400"
        >
          {uploading ? 'Uploading...' : `Upload ${files.length} File(s)`}
        </button>
      </form>
    </div>
  );
};

export default Upload;
