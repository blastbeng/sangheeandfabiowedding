import { useState, useEffect, useRef } from 'react';

const MAX_RETRIES = 10;
const RETRY_DELAY = 2000; // 2 seconds

const ThumbnailImage = ({ mediaId, apiUrl, alt, className, mediaType, onFinalError, src, fallbackSrc, rootClassName }) => {
  const [status, setStatus] = useState('loading'); // 'loading' | 'loaded' | 'error'
  const [retryCount, setRetryCount] = useState(0);
  const [imgSrc, setImgSrc] = useState(null);
  const mountedRef = useRef(true);
  const onFinalErrorRef = useRef(onFinalError);

  // Keep the ref updated without causing re-renders
  useEffect(() => {
    onFinalErrorRef.current = onFinalError;
  }, [onFinalError]);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Reset state when mediaId or src changes
  useEffect(() => {
    setStatus('loading');
    setRetryCount(0);
    setImgSrc(null);
  }, [mediaId, src]);

  useEffect(() => {
    if (status === 'loaded' || status === 'error') return;

    let timer = null;
    const url = src || `${apiUrl}/api/auth/media/${mediaId}/thumbnail/?retry=${retryCount}`;
    const img = new Image();

    img.onload = () => {
      if (mountedRef.current) {
        setImgSrc(url);
        setStatus('loaded');
      }
    };

    img.onerror = () => {
      if (!mountedRef.current) return;
      if (retryCount < MAX_RETRIES) {
        timer = setTimeout(() => {
          if (mountedRef.current) {
            setRetryCount(prev => prev + 1);
          }
        }, RETRY_DELAY);
      } else {
        setStatus('error');
        if (onFinalErrorRef.current) onFinalErrorRef.current(mediaId);
      }
    };

    img.src = url;

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [retryCount, apiUrl, mediaId, status, src]);

  if (status === 'loading') {
    return (
      <div className={`${className} bg-gray-200 animate-pulse flex items-center justify-center`}>
        <span className="text-gray-400 text-2xl">⏳</span>
      </div>
    );
  }

  if (status === 'error') {
    if (fallbackSrc) {
      return <img src={fallbackSrc} alt={alt} className={className} />;
    }
    return null; // parent will show failed placeholder via onFinalError
  }

  return (
    <div className={`relative ${rootClassName || ''}`}>
      <img src={imgSrc} alt={alt} className={className} />
      {mediaType === 'video' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/40 transition-colors">
          <div className="text-white text-5xl drop-shadow-lg">▶</div>
        </div>
      )}
    </div>
  );
};

export default ThumbnailImage;
