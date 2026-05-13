import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import authFetch from '../../utils/authFetch';

const CONCURRENCY = 6;          // upload up to 6 files simultaneously
const POLL_INTERVAL = 1000;     // ms between status checks
const STORAGE_KEY = 'pendingUploadTasks';

const Upload = () => {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [caption, setCaption] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL;

  // Per‑file status: { name, taskId, status: 'pending'|'uploading'|'success'|'error', error? }
  const [fileStatuses, setFileStatuses] = useState([]);

  // Keep track of active polling intervals so we can clear them on unmount
  const intervalsRef = useRef({});

  // ---------- mobile detection ----------
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // ---------- helpers for localStorage ----------
  const savePendingTasks = (tasks) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  };

  const clearPendingTasks = () => {
    localStorage.removeItem(STORAGE_KEY);
  };

  const getPendingTasks = () => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
      return [];
    }
  };

  // ---------- poll a single task ----------
  const pollTask = (taskId, fileName) => {
    const interval = setInterval(async () => {
      try {
        const res = await authFetch(`${API_URL}/api/auth/media/upload/status/${taskId}/`);
        const data = await res.json();

        if (data.status === 'SUCCESS') {
          clearInterval(interval);
          delete intervalsRef.current[taskId];

          setFileStatuses(prev =>
            prev.map(fs => fs.taskId === taskId ? { ...fs, status: 'success' } : fs)
          );

          // Remove this task from localStorage
          const pending = getPendingTasks().filter(t => t.taskId !== taskId);
          savePendingTasks(pending);
        } else if (data.status === 'FAILURE') {
          clearInterval(interval);
          delete intervalsRef.current[taskId];

          setFileStatuses(prev =>
            prev.map(fs =>
              fs.taskId === taskId
                ? { ...fs, status: 'error', error: data.error || t('upload_failed') }
                : fs
            )
          );

          const pending = getPendingTasks().filter(t => t.taskId !== taskId);
          savePendingTasks(pending);
        }
        // PENDING or STARTED → keep polling
      } catch (err) {
        // Temporary network error (e.g. browser backgrounded) – keep polling
        console.warn('[Upload] Polling fetch failed, will retry:', err);
      }
    }, POLL_INTERVAL);

    intervalsRef.current[taskId] = interval;
  };

  // ---------- resume pending tasks on mount ----------
  useEffect(() => {
    const pending = getPendingTasks();
    if (pending.length === 0) return;

    // Rebuild fileStatuses from stored tasks
    const restored = pending.map(p => ({
      name: p.fileName,
      taskId: p.taskId,
      status: 'uploading',
    }));
    setFileStatuses(restored);
    setUploading(true);

    // Start polling each
    pending.forEach(p => pollTask(p.taskId, p.fileName));

    // Cleanup intervals on unmount
    return () => {
      Object.values(intervalsRef.current).forEach(clearInterval);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------- watch for all files finished ----------
  useEffect(() => {
    if (!uploading || fileStatuses.length === 0) return;

    const allDone = fileStatuses.every(fs => fs.status === 'success' || fs.status === 'error');

    if (allDone) {
      setUploading(false);
      const successCount = fileStatuses.filter(fs => fs.status === 'success').length;
      const errorCount = fileStatuses.filter(fs => fs.status === 'error').length;

      if (errorCount === 0) {
        setSuccess(`${t('upload_successful')} ${successCount} ${t('files_processed')}`);
        setTimeout(() => navigate('/my-uploads'), 2000);
      } else {
        setError(`${t('upload_completed_with_errors')} (${successCount} ok, ${errorCount} failed)`);
      }
      clearPendingTasks();
    }
  }, [fileStatuses, uploading, navigate, t]);

  // ---------- file selection ----------
  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (isMobile) {
      const combined = [...files, ...selectedFiles];
      if (combined.length > 10) {
        setFiles(combined.slice(0, 10));
      } else {
        setFiles(combined);
      }
    } else {
      setFiles(prev => [...prev, ...selectedFiles]);
    }
  };

  const removeFile = (fileName) => {
    setFiles(prev => prev.filter(f => f.name !== fileName));
  };

  // ---------- start uploading all files ----------
  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError('');
    setSuccess('');

    const initialStatuses = files.map(f => ({
      name: f.name,
      fetchId: null,
      taskId: null,
      status: 'pending',
    }));
    setFileStatuses(initialStatuses);

    // Direct upload (no Background Fetch)
    const queue = [...files];
    const running = new Set();

    const uploadOne = async (file) => {
      setFileStatuses(prev =>
        prev.map(fs => fs.name === file.name ? { ...fs, status: 'uploading' } : fs)
      );

      const formData = new FormData();
      formData.append('file', file);
      formData.append('caption', caption);

      try {
        const res = await authFetch(`${API_URL}/api/auth/media/upload/`, {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();

        if (!res.ok) {
          setFileStatuses(prev =>
            prev.map(fs =>
              fs.name === file.name
                ? { ...fs, status: 'error', error: data.error || t('upload_failed') }
                : fs
            )
          );
          return;
        }

        const taskId = data.task_id;
        setFileStatuses(prev =>
          prev.map(fs =>
            fs.name === file.name ? { ...fs, taskId, status: 'uploading' } : fs
          )
        );

        const pending = getPendingTasks();
        pending.push({ taskId, fileName: file.name });
        savePendingTasks(pending);

        pollTask(taskId, file.name);
      } catch (err) {
        setFileStatuses(prev =>
          prev.map(fs =>
            fs.name === file.name
              ? { ...fs, status: 'error', error: t('error_during_upload') }
              : fs
          )
        );
      }
    };

    const worker = async () => {
      while (queue.length > 0) {
        const file = queue.shift();
        running.add(file);
        await uploadOne(file);
        running.delete(file);
      }
    };

    const workers = Array(Math.min(CONCURRENCY, queue.length))
      .fill()
      .map(() => worker());
    await Promise.all(workers);
  };

  // ---------- progress calculation ----------
  const total = fileStatuses.length;
  const completed = fileStatuses.filter(fs => fs.status === 'success' || fs.status === 'error').length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  // ---------- render ----------
  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="wedding-card p-8">
        <h2 className="text-3xl wedding-title text-center mb-2">📤 {t('Share Your Memories')}</h2>
        <p className="text-center text-gray-600 mb-6 italic">{t('upload_subtitle')}</p>

        {error && <div className="bg-red-50 border-2 border-red-300 text-red-700 px-4 py-3 rounded-xl mb-4">💔 {error}</div>}
        {success && <div className="bg-green-50 border-2 border-green-300 text-green-700 px-4 py-3 rounded-xl mb-4">✅ {success}</div>}

        {/* Progress bar */}
        {uploading && total > 0 && (
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>{t('uploading')}... {completed}/{total}</span>
              <span>{percent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-pink-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        )}

        {/* File list with status */}
        {fileStatuses.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-bold mb-3 text-pink-600">📁 {t('files_selected')} ({total})</h3>
            {fileStatuses.map((fs, idx) => (
              <div key={idx} className="bg-pink-50 p-3 rounded-xl mb-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm">📄 {fs.name}</span>
                  <span className="text-sm">
                    {fs.status === 'pending' && '⏳'}
                    {fs.status === 'uploading' && '⏳'}
                    {fs.status === 'success' && '✅'}
                    {fs.status === 'error' && '❌'}
                  </span>
                </div>
                {/* Per‑file progress bar */}
                <div className="mt-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      fs.status === 'success' ? 'bg-green-500 w-full' :
                      fs.status === 'error' ? 'bg-red-500 w-full' :
                      fs.status === 'uploading' ? 'bg-pink-400 animate-pulse w-full' :
                      'w-0'
                    }`}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* File picker (hidden during upload) */}
        {!uploading && (
          <>
            <div className="mb-6">
              <label htmlFor="file-upload" className="block text-gray-700 text-sm font-bold mb-2">📸 {t('select_photos_videos')}</label>
              <input id="file-upload" type="file" multiple accept="image/*,video/*" onChange={handleFileSelect} className="wedding-input w-full py-4" />
              <p className="text-sm text-gray-500 mt-2">✨ {t('supported_formats')}</p>

              {/* Mobile limit message */}
              {isMobile && (
                <p className="text-sm text-amber-600 mt-2">⚠️ {t('mobile_max_files_10')}</p>
              )}

              {/* Desktop many‑files warning */}
              {!isMobile && files.length > 10 && (
                <p className="text-sm text-amber-600 mt-2">⚠️ {t('desktop_many_files_warning')}</p>
              )}

              {/* General upload size notice */}
              <p className="text-sm text-gray-500 mt-2">ℹ️ {t('upload_size_notice')}</p>
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
                  <label className="block text-gray-700 text-sm font-bold mb-2">✏️ {t('add_captions_optional')}</label>
                  <input
                    type="text"
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    className="wedding-input w-full"
                    placeholder={t('add_sweet_memory')}
                  />
                </div>
              </>
            )}

            <button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              className="wedding-btn w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? `⏳ ${t('processing')}` : `💝 ${t('upload_memories')}`}
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default Upload;
