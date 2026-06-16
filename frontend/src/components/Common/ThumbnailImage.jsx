import { useState, useEffect, useRef } from 'react';
import authFetch from '../../utils/authFetch';

const MAX_RETRIES = 10;
const RETRY_DELAY = 2000; // 2 seconds

const ThumbnailImage = ({ mediaId, apiUrl, alt, className, mediaType, onFinalError, src, fallbackSrc, rootClassName }) => {
  const [status, setStatus] = useState('loading'); // 'loading' | 'loaded' | 'error'
  const [retryCount, setRetryCount] = useState(0);
  const [imgSrc, setImgSrc] = useState(null);
  const mountedRef = useRef(true);
  const onFinalErrorRef = useRef(onFinalError);
  const objectUrlRef = useRef(null);

  // Keep the ref updated without causing re-renders
  useEffect(() => {
    onFinalErrorRef.current = onFinalError;
  }, [onFinalError]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
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
    let cancelled = false;
    const url = src || `${apiUrl}/api/auth/media/${mediaId}/thumbnail/?retry=${retryCount}`;

    if (src) {
      // Direct src URL – use Image loading (no auth headers needed)
      const img = new Image();

      img.onload = () => {
        if (mountedRef.current && !cancelled) {
          setImgSrc(url);
          setStatus('loaded');
        }
      };

      img.onerror = () => {
        if (!mountedRef.current || cancelled) return;
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
    } else {
      // API URL – use authFetch to load as blob (enables auth + error handling)
      (async () => {
        try {
          const response = await authFetch(url);
          if (!mountedRef.current || cancelled) return;

          if (!response.ok) {
            // HTTP error – retry up to MAX_RETRIES
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
            return;
          }

          const blob = await response.blob();
          if (!mountedRef.current || cancelled) return;

          // Revoke previous object URL if any
          if (objectUrlRef.current) {
            URL.revokeObjectURL(objectUrlRef.current);
          }

          const objectUrl = URL.createObjectURL(blob);
          objectUrlRef.current = objectUrl;
          setImgSrc(objectUrl);
          setStatus('loaded');
        } catch (err) {
          // Network error (e.g., TLS/cert failure) – don't retry, fail immediately
          if (!mountedRef.current || cancelled) return;
          console.error('[ThumbnailImage] Network error, not retrying:', err);
          setStatus('error');
          if (onFinalErrorRef.current) onFinalErrorRef.current(mediaId);
        }
      })();
    }

    return () => {
      cancelled = true;
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
