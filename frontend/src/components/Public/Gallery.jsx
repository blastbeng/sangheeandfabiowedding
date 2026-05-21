import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';
import ThumbnailImage from '../Common/ThumbnailImage';
import ProtectedMediaPreview from '../Common/ProtectedMediaPreview';

const PAGE_SIZE = 20;
const STORAGE_KEY = 'galleryScrollState';

const Gallery = () => {
  const { t, i18n } = useTranslation();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [faceGroups, setFaceGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [selectedMediaType, setSelectedMediaType] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [failedMediaIds, setFailedMediaIds] = useState(new Set());
  const [faceGroupsVersion, setFaceGroupsVersion] = useState(0);
  const [viewMode, setViewMode] = useState('grid'); // 'gallery' | 'grid'
  const [selectedMedia, setSelectedMedia] = useState(null);
  const [modalImageState, setModalImageState] = useState('loading'); // 'loading' | 'thumbnail' | 'full'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);
  const API_URL = import.meta.env.VITE_API_URL;

  const sentinelRef = useRef(null);
  const hasRestoredScroll = useRef(false);
  const faceRowRef = useRef(null);
  const touchStartX = useRef(0);
  const isSwiping = useRef(false);
  const mediaRef = useRef(null);

  const scrollFaceRow = (direction) => {
    if (faceRowRef.current) {
      faceRowRef.current.scrollBy({
        left: direction * 200,
        behavior: 'smooth',
      });
    }
  };

  const fetchMedia = useCallback(async (pageNum, append = false) => {
    const params = new URLSearchParams();
    if (selectedUserId) params.append('user_id', selectedUserId);
    if (selectedGroupId) {
      params.append('face_group_id', selectedGroupId);
    }
    if (selectedMediaType !== 'all') params.append('media_type', selectedMediaType);
    if (viewMode === 'grid') {
      params.append('ordering', 'similarity');
    }
    params.append('page', pageNum);
    params.append('page_size', PAGE_SIZE);

    try {
      const res = await fetch(`${API_URL}/api/auth/media/public/?${params}`);
      const data = await res.json();
      const newMedia = Array.isArray(data) ? data : (data.results || []);
      if (append) {
        setMedia(prev => [...prev, ...newMedia]);
      } else {
        setMedia(newMedia);
        setFailedMediaIds(new Set());
        setFaceGroupsVersion(v => v + 1);
      }
      setHasMore(newMedia.length === PAGE_SIZE);
      setLoading(false);
      setLoadingMore(false);
    } catch (err) {
      logger.error('[Gallery] Failed to fetch media:', err);
      setLoading(false);
      setLoadingMore(false);
    }
  }, [selectedUserId, selectedGroupId, selectedMediaType, viewMode, API_URL]);

  const sortedMedia = useMemo(() => {
    if (viewMode !== 'grid') return media;

    // When using similarity ordering, respect backend order and just assign grid sizes
    if (viewMode === 'grid') {
      return media.map((item, index) => {
        const mod = index % 10;
        let gridColSpan = 1;
        let gridRowSpan = 1;
        if (mod === 0) {
          gridColSpan = 2;
          gridRowSpan = 2;
        } else if (mod === 3) {
          gridColSpan = 2;
        } else if (mod === 7) {
          gridRowSpan = 2;
        }
        return {
          ...item,
          gridColSpan,
          gridRowSpan,
        };
      });
    }

    // Separate videos and photos
    const videos = media.filter(item => item.media_type === 'video');
    const photos = media.filter(item => item.media_type === 'image');

    // Sort a group by face similarity (existing logic)
    const sortByFaces = (items) => {
      return [...items].sort((a, b) => {
        const aGroups = (a.face_tags || []).map(t => t.face_group_id).sort((x, y) => x - y);
        const bGroups = (b.face_tags || []).map(t => t.face_group_id).sort((x, y) => x - y);
        const aKey = aGroups.join(',');
        const bKey = bGroups.join(',');
        if (aKey === bKey) return 0;
        if (aGroups.length === 0 && bGroups.length > 0) return 1;
        if (bGroups.length === 0 && aGroups.length > 0) return -1;
        const aFirst = aGroups[0] || Infinity;
        const bFirst = bGroups[0] || Infinity;
        if (aFirst !== bFirst) return aFirst - bFirst;
        return aGroups.length - bGroups.length;
      });
    };

    const sortedVideos = sortByFaces(videos);
    const sortedPhotos = sortByFaces(photos);

    // Videos first, then photos
    const combined = [...sortedVideos, ...sortedPhotos];

    // Assign sizes: Instagram-like pattern
    return combined.map((item, index) => {
      const mod = index % 10;
      let gridColSpan = 1;
      let gridRowSpan = 1;
      if (mod === 0) {
        gridColSpan = 2;
        gridRowSpan = 2; // 2x2 large tile
      } else if (mod === 3) {
        gridColSpan = 2; // 2x1 wide tile
      } else if (mod === 7) {
        gridRowSpan = 2; // 1x2 tall tile
      }
      return {
        ...item,
        gridColSpan,
        gridRowSpan,
      };
    });
  }, [media, viewMode, sortBy]);

  // Restoration effect – only restore filters and scroll position, NOT media data
  useEffect(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const state = JSON.parse(saved);
        if (state.selectedUserId) setSelectedUserId(state.selectedUserId);
        if (state.selectedGroupId) setSelectedGroupId(state.selectedGroupId);
        if (state.selectedMediaType) setSelectedMediaType(state.selectedMediaType);
        if (state.sortBy) setSortBy(state.sortBy);
        if (state.scrollY !== undefined) {
          hasRestoredScroll.current = true;
          // Store scrollY in a ref so we can use it after media loads
          window.__galleryScrollY = state.scrollY;
        }
      } catch (e) {
        // ignore corrupted data
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll restoration effect
  useEffect(() => {
    if (hasRestoredScroll.current && media.length > 0) {
      const scrollY = window.__galleryScrollY;
      if (scrollY !== undefined) {
        window.scrollTo(0, scrollY);
        delete window.__galleryScrollY;
      }
      hasRestoredScroll.current = false;
    }
  }, [media]);

  // Fetch media effect – always fetch on mount and when filters change
  useEffect(() => {
    setPage(1);
    setHasMore(true);
    setLoading(true);
    fetchMedia(1, false);
  }, [selectedUserId, selectedGroupId, selectedMediaType, fetchMedia]);

  // Save only filters and scroll position on unmount (not media data)
  useEffect(() => {
    return () => {
      const state = {
        selectedUserId,
        selectedGroupId,
        selectedMediaType,
        sortBy,
        scrollY: window.scrollY,
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    };
  }, [selectedUserId, selectedGroupId, selectedMediaType, sortBy]);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/face-groups/`)
      .then(res => res.json())
      .then(data => setFaceGroups(data))
      .catch(err => logger.error('[Gallery] Failed to fetch face groups:', err));
  }, [faceGroupsVersion]);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/users/public/?has_approved_media=true`)
      .then(res => res.json())
      .then(data => setUsers(Array.isArray(data) ? data : []))
      .catch(err => logger.error('[Gallery] Failed to fetch users:', err));
  }, [API_URL]);

  useEffect(() => {
    if (!hasMore || loadingMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          setLoadingMore(true);
          const nextPage = page + 1;
          setPage(nextPage);
          fetchMedia(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );
    const currentSentinel = sentinelRef.current;
    if (currentSentinel) observer.observe(currentSentinel);
    return () => {
      if (currentSentinel) observer.unobserve(currentSentinel);
    };
  }, [hasMore, loadingMore, page, fetchMedia]);

  // Map i18n language to locale string for date formatting
  const localeMap = { it: 'it-IT', ko: 'ko-KR', en: 'en-US' };
  const dateLocale = localeMap[i18n.language] || 'it-IT';

  const navigableMedia = viewMode === 'grid' ? sortedMedia : media;
  const currentIndex = selectedMedia
    ? navigableMedia.findIndex(item => item.id === selectedMedia.id)
    : -1;

  const goToPrev = () => {
    if (currentIndex > 0) setSelectedMedia(navigableMedia[currentIndex - 1]);
  };
  const goToNext = () => {
    if (currentIndex < navigableMedia.length - 1) setSelectedMedia(navigableMedia[currentIndex + 1]);
  };

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };
  const handleTouchEnd = (e) => {
    const deltaX = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(deltaX) > 50) {
      isSwiping.current = true;
      setTimeout(() => { isSwiping.current = false; }, 100);
      if (deltaX > 0 && currentIndex > 0) {
        goToPrev();
      } else if (deltaX < 0 && currentIndex < navigableMedia.length - 1) {
        goToNext();
      }
    } else {
      // Tap (no significant swipe) → close modal
      setSelectedMedia(null);
    }
  };

  // Escape and arrow key listener to close/navigate modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedMedia(null);
      } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
        goToPrev();
      } else if (e.key === 'ArrowRight' && currentIndex < navigableMedia.length - 1) {
        goToNext();
      }
    };
    if (selectedMedia) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [selectedMedia, currentIndex, navigableMedia.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Preload modal media and manage loading state
  useEffect(() => {
    if (!selectedMedia) {
      setModalImageState('loading');
      return;
    }
    setModalImageState('loading');
    const fullUrl = `${API_URL}/api/auth/media/${selectedMedia.id}/file/`;
    if (selectedMedia.media_type === 'image') {
      const thumbUrl = `${API_URL}/api/auth/media/${selectedMedia.id}/thumbnail/?retry=0`;
      let thumbLoaded = false;
      let fullLoaded = false;
      let cancelled = false;

      const transition = () => {
        if (cancelled) return;
        if (fullLoaded) {
          setModalImageState('full');
        } else if (thumbLoaded) {
          setModalImageState('thumbnail');
        }
      };

      // Preload thumbnail
      const thumbImg = new Image();
      thumbImg.onload = () => {
        thumbLoaded = true;
        transition();
      };
      thumbImg.onerror = () => {
        // Thumbnail failed – go straight to full (will show full image loading)
        fullLoaded = true;
        transition();
      };
      thumbImg.src = thumbUrl;
      if (thumbImg.complete) {
        // Already cached – fire immediately
        thumbLoaded = true;
        transition();
      }

      // Preload full image
      const fullImg = new Image();
      fullImg.onload = () => {
        fullLoaded = true;
        transition();
      };
      fullImg.onerror = () => {
        fullLoaded = true; // ProtectedMediaPreview handles errors
        transition();
      };
      fullImg.src = fullUrl;
      if (fullImg.complete) {
        fullLoaded = true;
        transition();
      }

      return () => {
        cancelled = true;
        thumbImg.onload = null;
        thumbImg.onerror = null;
        fullImg.onload = null;
        fullImg.onerror = null;
      };
    } else {
      // For video, start streaming immediately
      setModalImageState('full');
    }
  }, [selectedMedia, API_URL]);

  const handleShare = async () => {
    const shareUrl = `${window.location.origin}/api/auth/media/${selectedMedia.id}/share/`;
    if (navigator.share) {
      try {
        await navigator.share({
          title: selectedMedia.caption || t('beautiful_moment'),
          url: shareUrl,
        });
      } catch (err) {
        // user cancelled or error – no action needed
      }
    } else {
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(shareUrl);
        setCopyFeedback(true);
        setTimeout(() => setCopyFeedback(false), 2000);
      } catch (err) {
        // clipboard failed – silently ignore
      }
    }
  };

  const handleFullscreen = () => {
    const el = mediaRef.current;
    if (!el) return;
    try {
      if (el.requestFullscreen) {
        el.requestFullscreen().catch(err => {
          logger.error('[Gallery] Fullscreen request failed:', err);
        });
      } else if (el.webkitRequestFullscreen) {
        el.webkitRequestFullscreen();
      } else if (el.msRequestFullscreen) {
        el.msRequestFullscreen();
      }
    } catch (err) {
      logger.error('[Gallery] Fullscreen error:', err);
    }
  };

  const handleDownload = async () => {
    const url = `${API_URL}/api/auth/media/${selectedMedia.id}/file/`;
    try {
      const res = await authFetch(url);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = selectedMedia.original_filename || `media_${selectedMedia.id}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      logger.error('[Gallery] Download failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heartDecoration inline-block">💝</span>
        <p className="mt-4 text-gray-600 text-lg">{t('loading_memories')}</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="text-center mb-8">
        <h2 className="text-4xl wedding-title mb-2">{t('gallery_title')}</h2>
        <p className="text-gray-600 italic">{t('gallery_subtitle')}</p>
      </div>

      {/* View mode toggle */}
      <div className="flex justify-center mb-4">
        <div className="inline-flex rounded-lg border border-gray-200 bg-white shadow-sm">
          <button
            onClick={() => setViewMode('grid')}
            className={`px-4 py-2 text-sm font-medium rounded-l-lg transition-colors ${
              viewMode === 'grid'
                ? 'bg-pink-500 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t('grid_mode') || 'Grid'}
          </button>
          <button
            onClick={() => setViewMode('gallery')}
            className={`px-4 py-2 text-sm font-medium rounded-r-lg transition-colors ${
              viewMode === 'gallery'
                ? 'bg-pink-500 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t('gallery_mode') || 'Gallery'}
          </button>
        </div>
      </div>

          {/* Face group row */}
          {faceGroups.length > 0 && (
            <div className="mb-6">
              <label className="block text-sm text-gray-600 mb-1">{t('filter_by_person')}</label>
              <div className="flex items-center gap-1">
                {/* Left arrow */}
                <button
                  onClick={() => scrollFaceRow(-1)}
                  className="flex-shrink-0 w-8 h-8 rounded-full bg-white shadow flex items-center justify-center text-gray-500 hover:text-pink-600"
                  aria-label="Scroll left"
                >
                  ‹
                </button>

                {/* Scrollable row – now with a visible scrollbar */}
                <div
                  ref={faceRowRef}
                  className="flex gap-3 overflow-x-auto pb-2 flex-1"
                  style={{ scrollSnapType: 'x mandatory', scrollbarWidth: 'thin' }}
                >
                  {faceGroups.map(group => (
                    <button
                      key={group.id}
                      onClick={() => setSelectedGroupId(prev => prev === group.id ? null : group.id)}
                      className={`flex flex-col items-center gap-1 flex-shrink-0 transition-transform hover:scale-105 ${
                        selectedGroupId === group.id ? 'ring-2 ring-pink-500 rounded-full' : ''
                      }`}
                      style={{ scrollSnapAlign: 'start' }}
                    >
                      <img
                        src={group.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                        alt={group.user_display_name || ''}
                        className="w-12 h-12 rounded-full object-cover border-2 border-white shadow-sm"
                        onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                      />
                    </button>
                  ))}
                </div>

                {/* Right arrow */}
                <button
                  onClick={() => scrollFaceRow(1)}
                  className="flex-shrink-0 w-8 h-8 rounded-full bg-white shadow flex items-center justify-center text-gray-500 hover:text-pink-600"
                  aria-label="Scroll right"
                >
                  ›
                </button>
              </div>
            </div>
          )}

          {/* Filter controls */}
          <div className="mb-6 flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm text-gray-600 mb-1">{t('filter_by_type')}</label>
              <select
                value={selectedMediaType}
                onChange={e => setSelectedMediaType(e.target.value)}
                className="wedding-input"
              >
                <option value="all">{t('filter_all_types')}</option>
                <option value="image">{t('filter_photos')}</option>
                <option value="video">{t('filter_videos')}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">{t('Search by user')}</label>
              <select
                value={selectedUserId}
                onChange={e => setSelectedUserId(e.target.value)}
                className="wedding-input"
              >
                <option value="">{t('All users')}</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.first_name || user.last_name
                      ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                      : user.username}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedGroupId && (() => {
            const group = faceGroups.find(g => g.id === selectedGroupId);
            return (
              <div className="mb-4 flex items-center gap-2 flex-wrap">
                <span className="text-sm text-gray-600">{t('Filtering by')}:</span>
                <span className="inline-flex items-center gap-1 bg-pink-50 rounded-full px-2 py-1">
                  <img
                    src={group?.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                    alt=""
                    className="w-6 h-6 rounded-full object-cover border border-pink-200"
                    onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                  />
                  <button
                    onClick={() => setSelectedGroupId(null)}
                    className="text-pink-600 hover:text-pink-800 text-xs leading-none"
                    title={t('Remove filter')}
                  >
                    ✕
                  </button>
                </span>
                <button
                  onClick={() => setSelectedGroupId(null)}
                  className="text-xs text-pink-600 underline hover:text-pink-800 ml-2"
                >
                  {t('Clear filter')}
                </button>
              </div>
            );
          })()}
      {!loading && media.length === 0 ? (
        <div className="text-center py-20 wedding-card">
          <span className="text-6xl floating-heart inline-block">🌸</span>
          <p className="mt-4 text-gray-600 text-lg">{t('no_photos_yet')}</p>
          <p className="text-gray-500 text-sm">{t('be_first_to_share')}</p>
        </div>
      ) : viewMode === 'gallery' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-0">
          {media.map((item) => {
            const isFailed = failedMediaIds.has(item.id);
            const faceTags = item.face_tags || [];

            return (
              <div key={item.id} className="gallery-item bg-white shadow-lg">
                {isFailed ? (
                  <div className="w-full aspect-square bg-gray-100 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <span className="text-4xl">🖼️‍🗑️</span>
                      <p className="text-xs mt-1">{t('file_unavailable')}</p>
                    </div>
                  </div>
                ) : (
                  <div
                    onClick={() => setSelectedMedia(item)}
                    className="block relative cursor-pointer"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter') setSelectedMedia(item); }}
                  >
                    <ThumbnailImage
                      mediaId={item.id}
                      apiUrl={API_URL}
                      alt={item.caption || t('beautiful_moment')}
                      className="w-full aspect-square object-cover"
                      mediaType={item.media_type}
                      onFinalError={(id) => setFailedMediaIds(prev => new Set(prev).add(id))}
                    />
                  </div>
                )}
                <div className="p-3">
                  {/* Uploader info */}
                  {item.uploader_username && (
                    <div className="mb-2 flex items-center gap-1">
                      <span className="text-xs text-gray-500">{t('uploaded_by')}:</span>
                      <Link to={`/user/${item.user_id}`} className="inline-flex items-center gap-1 hover:opacity-80">
                        <img
                          src={item.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                          alt={item.uploader_username}
                          className="w-6 h-6 rounded-full object-cover border border-pink-200"
                          onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                        />
                        <span className="text-sm text-gray-600 font-medium">
                          {item.uploader_first_name || item.uploader_last_name
                            ? `${item.uploader_first_name || ''} ${item.uploader_last_name || ''}`.trim()
                            : item.uploader_username}
                        </span>
                      </Link>
                    </div>
                  )}
                  <p className="text-gray-700 text-sm mb-2 line-clamp-2">
                    {item.caption || t('beautiful_moment')}
                  </p>
                  {item.media_type === 'image' && faceTags.length > 0 && (
                    <div className="mt-2 flex items-center gap-1">
                      <span className="text-xs text-gray-500">{t('in_this_photo')}:</span>
                      <div className="inline-flex overflow-x-auto gap-1">
                        {faceTags.map(tag => (
                          <button
                            key={tag.face_group_id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedGroupId(prev => prev === tag.face_group_id ? null : tag.face_group_id);
                            }}
                            className={`flex-shrink-0 w-6 h-6 rounded-full overflow-hidden border-2 transition-colors ${
                              selectedGroupId === tag.face_group_id ? 'border-pink-500' : 'border-white'
                            }`}
                          >
                            <img
                              src={tag.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                              alt=""
                              className="w-full h-full object-cover"
                              onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-gray-500 text-xs">
                    {t('uploaded_at')}: {new Date(item.uploaded_at).toLocaleDateString(dateLocale, { day: '2-digit', month: '2-digit', year: 'numeric' })} {new Date(item.uploaded_at).toLocaleTimeString(dateLocale, { hour: '2-digit', minute: '2-digit', hour12: false })}
                  </p>
                </div>
              </div>
            );
          })}
          {hasMore && (
            <div ref={sentinelRef} className="col-span-full flex justify-center py-4">
              {loadingMore ? (
                <span className="text-gray-500">{t('loading_more')}</span>
              ) : (
                <span className="text-gray-400">&#8203;</span>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Grid mode: 3-column Instagram-style grid with varying sizes */
        <div className="grid grid-cols-3 gap-0 auto-rows-[150px] grid-flow-dense bg-gray-100">
          {sortedMedia.map((item) => {
            const isFailed = failedMediaIds.has(item.id);
            return (
              <div
                key={item.id}
                onClick={() => setSelectedMedia(item)}
                className={`block relative cursor-pointer h-full overflow-hidden ${
                  item.gridColSpan === 2 ? 'col-span-2' : ''
                } ${
                  item.gridRowSpan === 2 ? 'row-span-2' : ''
                }`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') setSelectedMedia(item); }}
              >
                {isFailed ? (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <span className="text-2xl">🖼️‍🗑️</span>
                  </div>
                ) : (
                  <ThumbnailImage
                    mediaId={item.id}
                    apiUrl={API_URL}
                    alt={item.caption || t('beautiful_moment')}
                    className="w-full h-full object-cover"
                    rootClassName="h-full"
                    mediaType={item.media_type}
                    onFinalError={(id) => setFailedMediaIds(prev => new Set(prev).add(id))}
                  />
                )}
              </div>
            );
          })}
          {hasMore && (
            <div ref={sentinelRef} className="col-span-full flex justify-center py-4">
              {loadingMore ? (
                <span className="text-gray-500">{t('loading_more')}</span>
              ) : (
                <span className="text-gray-400">&#8203;</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Fullscreen modal */}
      {selectedMedia && (
        <div
          key={selectedMedia.id}
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
          onClick={() => {
            if (isSwiping.current) return;
            setSelectedMedia(null);
          }}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {/* Close button */}
          <button
            onClick={() => setSelectedMedia(null)}
            onTouchStart={(e) => e.stopPropagation()}
            onTouchEnd={(e) => e.stopPropagation()}
            className="absolute top-4 right-4 text-white text-3xl hover:text-gray-300 z-10"
            aria-label="Close"
          >
            &times;
          </button>

          {/* Left arrow */}
          {currentIndex > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); goToPrev(); }}
              onTouchStart={(e) => e.stopPropagation()}
              onTouchEnd={(e) => e.stopPropagation()}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white text-4xl hover:text-gray-300 z-10 bg-black bg-opacity-50 rounded-full w-12 h-12 flex items-center justify-center"
              aria-label="Previous"
            >
              ‹
            </button>
          )}

          {/* Right arrow */}
          {currentIndex < navigableMedia.length - 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); goToNext(); }}
              onTouchStart={(e) => e.stopPropagation()}
              onTouchEnd={(e) => e.stopPropagation()}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white text-4xl hover:text-gray-300 z-10 bg-black bg-opacity-50 rounded-full w-12 h-12 flex items-center justify-center"
              aria-label="Next"
            >
              ›
            </button>
          )}

          {/* Content container – stop click and touch propagation */}
          <div
            className="relative max-w-4xl w-full h-full max-h-full overflow-hidden bg-white rounded-lg shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Media area – fixed height, no scroll */}
            <div
              className="flex-1 min-h-0 relative bg-black"
              ref={mediaRef}
              {...(isFullscreen ? { onTouchStart: handleTouchStart, onTouchEnd: handleTouchEnd } : {})}
            >
              {isFullscreen && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (document.exitFullscreen) {
                      document.exitFullscreen();
                    }
                  }}
                  onTouchStart={(e) => e.stopPropagation()}
                  onTouchEnd={(e) => e.stopPropagation()}
                  className="absolute top-2 right-2 z-20 bg-black bg-opacity-50 text-white rounded-full p-2 hover:bg-opacity-75"
                  aria-label="Exit fullscreen"
                >
                  ✕
                </button>
              )}
              {modalImageState === 'loading' ? (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-200">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
                </div>
              ) : modalImageState === 'thumbnail' ? (
                <img
                  src={`${API_URL}/api/auth/media/${selectedMedia.id}/thumbnail/`}
                  alt=""
                  className="absolute inset-0 w-full h-full object-contain"
                />
              ) : (
                <>
                  {selectedMedia.media_type === 'video' ? (
                    <video
                      key={selectedMedia.id}
                      src={`${API_URL}/api/auth/media/${selectedMedia.id}/file/`}
                      controls
                      autoPlay
                      playsInline
                      className="absolute inset-0 w-full h-full object-contain"
                      onError={() => setModalImageState('loading')}
                    >
                      Your browser does not support the video tag.
                    </video>
                  ) : (
                    <img
                      key={selectedMedia.id}
                      src={`${API_URL}/api/auth/media/${selectedMedia.id}/file/`}
                      alt={selectedMedia.caption || t('beautiful_moment')}
                      className="absolute inset-0 w-full h-full object-contain"
                    />
                  )}
                  {/* Fullscreen button */}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleFullscreen(); }}
                    onTouchStart={(e) => e.stopPropagation()}
                    onTouchEnd={(e) => e.stopPropagation()}
                    className="absolute bottom-2 right-2 z-10 bg-black bg-opacity-50 text-white rounded-full p-2 hover:bg-opacity-75 transition-opacity"
                    title="Fullscreen"
                  >
                    ⛶
                  </button>
                </>
              )}
            </div>

            {/* Details section */}
            <div className="p-4">
              {/* Uploader info */}
              {selectedMedia.uploader_username && (
                <div className="mb-2 flex items-center gap-1">
                  <span className="text-xs text-gray-500">{t('uploaded_by')}:</span>
                  <Link
                    to={`/user/${selectedMedia.user_id}`}
                    className="inline-flex items-center gap-1 hover:opacity-80"
                  >
                    <img
                      src={selectedMedia.uploader_profile_picture || 'https://i.imgur.com/V4RclNb.png'}
                      alt={selectedMedia.uploader_username}
                      className="w-6 h-6 rounded-full object-cover border border-pink-200"
                      onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                    />
                    <span className="text-sm text-gray-600 font-medium">
                      {selectedMedia.uploader_first_name || selectedMedia.uploader_last_name
                        ? `${selectedMedia.uploader_first_name || ''} ${selectedMedia.uploader_last_name || ''}`.trim()
                        : selectedMedia.uploader_username}
                    </span>
                  </Link>
                </div>
              )}

              {/* Caption */}
              <p className="text-gray-700 text-sm mb-2">
                {selectedMedia.caption || t('beautiful_moment')}
              </p>

              {/* Face tags */}
              {selectedMedia.media_type === 'image' && selectedMedia.face_tags?.length > 0 && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="text-xs text-gray-500">{t('in_this_photo')}:</span>
                  <div className="inline-flex gap-1">
                    {selectedMedia.face_tags.map(tag => (
                      <button
                        key={tag.face_group_id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedGroupId(prev => prev === tag.face_group_id ? null : tag.face_group_id);
                        }}
                        className={`flex-shrink-0 w-6 h-6 rounded-full overflow-hidden border-2 transition-colors ${
                          selectedGroupId === tag.face_group_id ? 'border-pink-500' : 'border-white'
                        }`}
                      >
                        <img
                          src={tag.thumbnail_url || 'https://i.imgur.com/V4RclNb.png'}
                          alt=""
                          className="w-full h-full object-cover"
                          onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Date */}
              <p className="text-gray-500 text-xs mt-2">
                {t('uploaded_at')}: {new Date(selectedMedia.uploaded_at).toLocaleDateString(dateLocale, { day: '2-digit', month: '2-digit', year: 'numeric' })} {new Date(selectedMedia.uploaded_at).toLocaleTimeString(dateLocale, { hour: '2-digit', minute: '2-digit', hour12: false })}
              </p>

              {/* Share button */}
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={(e) => { e.stopPropagation(); handleShare(); }}
                  onTouchStart={(e) => e.stopPropagation()}
                  onTouchEnd={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-pink-500 text-white rounded-full hover:bg-pink-600 transition-colors"
                >
                  <span>📤</span> {t('share_this_memory')}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDownload(); }}
                  onTouchStart={(e) => e.stopPropagation()}
                  onTouchEnd={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-blue-500 text-white rounded-full hover:bg-blue-600 transition-colors"
                >
                  <span>⬇️</span> {t('download') || 'Download'}
                </button>
                {copyFeedback && (
                  <span className="text-xs text-green-600">{t('link_copied')}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Gallery;
