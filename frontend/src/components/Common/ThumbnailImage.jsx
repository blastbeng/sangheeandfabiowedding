import { useEffect, useMemo, useRef, useState } from 'react';

const MAX_RETRIES = 2;
const RETRY_DELAY = 1500;

const ThumbnailImage = ({
  mediaId,
  apiUrl,
  alt,
  className,
  mediaType,
  onFinalError,
  src,
  fallbackSrc,
  rootClassName,
  size = 'grid',
  loading = 'lazy',
  fetchPriority,
}) => {
  const baseUrl = useMemo(() => {
    if (src) return src;
    if (!mediaId) return null;
    // `v=5` is part of the URL so the browser can cache the rendition
    // forever (immutable); bump it when the generation changes.
    return `${apiUrl}/api/auth/media/${mediaId}/thumbnail/?size=${size}&v=5`;
  }, [src, mediaId, apiUrl, size]);

  const [status, setStatus] = useState('loading'); // 'loading' | 'loaded' | 'error'
  const [retryCount, setRetryCount] = useState(0);
  const imgRef = useRef(null);

  useEffect(() => {
    setStatus('loading');
    setRetryCount(0);
  }, [baseUrl]);

  // A cached image can be complete before React attaches onLoad.
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete && img.naturalWidth > 0) {
      setStatus('loaded');
    }
  }, [baseUrl, retryCount]);

  const url = retryCount > 0 && baseUrl ? `${baseUrl}&retry=${retryCount}` : baseUrl;

  const handleError = () => {
    if (retryCount < MAX_RETRIES) {
      window.setTimeout(() => setRetryCount((count) => count + 1), RETRY_DELAY);
      return;
    }
    setStatus('error');
    if (onFinalError) onFinalError(mediaId);
  };

  if (!baseUrl) return null;

  if (status === 'error') {
    if (fallbackSrc) {
      return <img src={fallbackSrc} alt={alt} className={className} loading={loading} />;
    }
    return null;
  }

  return (
    <div className={`relative ${rootClassName || ''}`}>
      {status === 'loading' && (
        <div className="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center">
          <span className="text-gray-400 text-2xl">⏳</span>
        </div>
      )}
      <img
        ref={imgRef}
        src={url}
        alt={alt}
        className={className}
        loading={loading}
        decoding="async"
        fetchPriority={fetchPriority}
        onLoad={() => setStatus('loaded')}
        onError={handleError}
        style={{
          opacity: status === 'loaded' ? 1 : 0,
          transition: 'opacity 150ms ease-in',
        }}
      />
      {mediaType === 'video' && status === 'loaded' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/40 transition-colors">
          <div className="text-white text-5xl drop-shadow-lg">▶</div>
        </div>
      )}
    </div>
  );
};

export default ThumbnailImage;
