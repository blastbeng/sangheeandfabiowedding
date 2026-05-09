import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';

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
    files.forEach((file) => {
      formData.append('files', file);
      formData.append('captions', captions[file.name] || '');
    });

    try {
      const res = await authFetch(`${API_URL}/api/auth/media/upload/`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || t('upload_failed'));
        setUploading(false);
        return;
      }

      const taskId = data.task_id;
      setSuccess(t('upload_queued_processing'));

      // Poll task status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await authFetch(`${API_URL}/api/auth/media/upload/status/${taskId}/`);
          const statusData = await statusRes.json();
          if (statusData.status === 'SUCCESS') {
            clearInterval(pollInterval);
            const result = statusData.result;
            if (result.errors && result.errors.length > 0) {
              setError(`${t('upload_completed_with_errors')} ${result.errors.join(', ')}`);
            } else {
              setSuccess(`${t('upload_successful')} ${result.uploaded?.length || 0} ${t('files_processed')}`);
              setTimeout(() => navigate('/my-uploads'), 2000);
            }
            setUploading(false);
          } else if (statusData.status === 'FAILURE') {
            clearInterval(pollInterval);
            setError(`${t('upload_failed_error')} ${statusData.error || t('Unknown error')}`);
            setUploading(false);
          }
          // If PENDING or STARTED, keep polling
        } catch (err) {
          clearInterval(pollInterval);
          setError(t('failed_check_status'));
          setUploading(false);
        }
      }, 2000);
    } catch (err) {
      setError(t('error_during_upload'));
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">📤 {t('Share Your Memories')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">{t('upload_subtitle')}</p>

        {error && <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4">💔 {error}</div>}
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">✅ {success}</div>}

        <div className="mb-6">
          <label htmlFor="file-upload" className="block text-gray-700 text-sm font-bold mb-2">📸 {t('select_photos_videos')}</label>
          <input id="file-upload" type="file" multiple accept="image/*,video/*" onChange={handleFileSelect} className="wedding-input w-full py-4" />
          <p className="text-sm text-gray-500 mt-2">✨ {t('supported_formats')}</p>
        </div>

        {files.length > 0 && (
          <>
            <div className="mb-6">
              <h3 className="text-lg font-bold mb-3 text-pink-600">📁 {t('files_selected')} ({files.length})</h3>
              {files.map((file, index) => (
                <div key={index} className="bg-pink-50 p-3 rounded-xl mb-2 flex justify-between items-center">
                  <span className="text-sm">📄 {file.name}</span>
                  <button onClick={() => removeFile(file.name)} className="text-red-500 hover:text-red-700 text-sm">❌ {t('remove')}</button>
                </div>
              ))}
            </div>
            <div className="mb-6">
              <h3 className="text-lg font-bold mb-3 text-pink-600">✏️ {t('add_captions_optional')}</h3>
              {files.map((file, index) => (
                <div key={index} className="mb-3">
                  <label className="block text-gray-700 text-xs font-bold mb-1">📝 {file.name}</label>
                  <input type="text" value={captions[file.name] || ''} onChange={(e) => handleCaptionChange(file.name, e.target.value)} className="wedding-input w-full text-sm" placeholder={t('add_sweet_memory')} />
                </div>
              ))}
            </div>
          </>
        )}

        <button onClick={handleUpload} disabled={files.length === 0 || uploading} className="wedding-btn w-full disabled:opacity-50 disabled:cursor-not-allowed">
          {uploading ? `⏳ ${t('processing')}` : `💝 ${t('upload_memories')}`}
        </button>
      </div>
    </div>
  );
};

export default Upload;
