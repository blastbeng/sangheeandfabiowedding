// public/sw.js
const POLL_INTERVAL = 2000;
const API_ORIGIN = self.location.origin;

// ---------- IndexedDB token store ----------
function openTokenDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TokenStore', 1);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('tokens')) {
        db.createObjectStore('tokens', { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getAuthToken() {
  const db = await openTokenDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('tokens', 'readonly');
    const store = tx.objectStore('tokens');
    const getReq = store.get('accessToken');
    getReq.onsuccess = () => resolve(getReq.result?.value);
    getReq.onerror = () => reject(getReq.error);
  });
}

async function setAuthToken(token) {
  const db = await openTokenDB();
  const tx = db.transaction('tokens', 'readwrite');
  const store = tx.objectStore('tokens');
  store.put({ id: 'accessToken', value: token });
  await tx.complete;
}

// ---------- Poll task status ----------
async function pollTaskStatus(taskId, fetchId) {
  const statusUrl = `${API_ORIGIN}/api/auth/media/upload/status/${taskId}/`;

  while (true) {
    try {
      const token = await getAuthToken();
      if (!token) {
        await new Promise(r => setTimeout(r, POLL_INTERVAL));
        continue;
      }
      const res = await fetch(statusUrl, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();

      if (data.status === 'SUCCESS') {
        const clients = await self.clients.matchAll();
        clients.forEach(client =>
          client.postMessage({ type: 'TASK_SUCCESS', taskId, fetchId })
        );
        await self.registration.showNotification('Upload complete', {
          body: 'Your file has been processed.',
          icon: '/icon-192.png'
        });
        break;
      } else if (data.status === 'FAILURE') {
        const clients = await self.clients.matchAll();
        clients.forEach(client =>
          client.postMessage({
            type: 'TASK_ERROR',
            taskId,
            fetchId,
            error: data.error || 'Processing failed'
          })
        );
        await self.registration.showNotification('Upload failed', {
          body: data.error || 'Processing failed'
        });
        break;
      }
    } catch (err) {
      console.error('[SW] Polling error:', err);
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

// ---------- Background Fetch Events ----------
self.addEventListener('backgroundfetchsuccess', (event) => {
  const bgFetch = event.registration;
  event.waitUntil(
    (async () => {
      const records = await bgFetch.matchAll();
      if (records.length === 0) return;
      const response = await records[0].responseReady;
      const cloned = response.clone();
      let taskId;
      try {
        const data = await cloned.json();
        taskId = data.task_id;
      } catch (e) {
        console.error('[SW] Failed to parse upload response:', e);
        const clients = await self.clients.matchAll();
        clients.forEach(c =>
          c.postMessage({ type: 'UPLOAD_ERROR', fetchId: bgFetch.id, error: 'Invalid response' })
        );
        return;
      }

      const clients = await self.clients.matchAll();
      clients.forEach(c =>
        c.postMessage({ type: 'UPLOAD_COMPLETED', fetchId: bgFetch.id, taskId })
      );

      await pollTaskStatus(taskId, bgFetch.id);
    })()
  );
});

self.addEventListener('backgroundfetchfail', (event) => {
  const bgFetch = event.registration;
  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll();
      clients.forEach(c =>
        c.postMessage({ type: 'UPLOAD_ERROR', fetchId: bgFetch.id, error: 'Upload failed' })
      );
    })()
  );
});

self.addEventListener('backgroundfetchabort', (event) => {
  // Optional: handle abort
});

self.addEventListener('backgroundfetchclick', (event) => {
  event.waitUntil(self.clients.openWindow('/'));
});

// ---------- Message handler (token updates) ----------
self.addEventListener('message', (event) => {
  if (event.data.type === 'SET_TOKEN') {
    event.waitUntil(setAuthToken(event.data.token));
  }
});
