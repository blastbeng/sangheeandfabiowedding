import { useEffect, useState } from 'react';
import authFetch from '../../utils/authFetch';
import logger from '../../utils/logger';

const ProtectedMediaPreview = ({ fileUrl, mediaType, className, alt }) => {
  const [blobUrl, setBlobUrl] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;

    const fetchMedia = async () => {
      try {
        const res = await authFetch(fileUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        if (!cancelled) {
          objectUrl = URL.createObjectURL(blob);
          setBlobUrl(objectUrl);
        }
      } catch (err) {
        logger.error('[ProtectedMediaPreview] Failed to load:', fileUrl, err);
        if (!cancelled) setError(true);
      }
    };

    fetchMedia();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileUrl]);

  if (error) {
    return <span className="text-gray-400">📁</span>;
  }

  if (!blobUrl) {
    return <div className="animate-pulse bg-gray-200 w-full h-full" />;
  }

  if (mediaType === 'video') {
    return (
      <video src={blobUrl} className={className} controls />
    );
  }

  return (
    <img src={blobUrl} alt={alt || 'Media'} className={className} />
  );
};

export default ProtectedMediaPreview;
