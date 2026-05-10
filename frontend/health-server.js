const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5173;
const DIST_DIR = path.join(__dirname, 'dist');
const HEALTH_LOG = path.join(__dirname, 'healthcheck.log');

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

function hasFileExtension(url) {
  const lastSegment = url.split('/').pop();
  return lastSegment.includes('.');
}

function logHealthCheck() {
  const timestamp = new Date().toISOString();
  fs.appendFileSync(HEALTH_LOG, `${timestamp} - healthcheck\n`);
}

function serveStatic(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0]; // ignore query params

  // Healthcheck endpoint – log to file only, no console output
  if (req.method === 'GET' && url === '/health') {
    logHealthCheck();
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('OK');
    return;
  }

  // Console log for all other requests
  console.log(`${new Date().toISOString()} ${req.method} ${url}`);

  // Determine the file to serve
  const isRoot = url === '/';
  const requestPath = isRoot ? '/index.html' : url;
  const filePath = path.join(DIST_DIR, requestPath);

  // Helper to serve a file with appropriate caching headers
  const serveWithCache = (res, filePath, cacheType) => {
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
        return;
      }
      const headers = { 'Content-Type': contentType };
      if (cacheType === 'html') {
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
      } else if (cacheType === 'hashed') {
        headers['Cache-Control'] = 'public, max-age=31536000, immutable';
      } else {
        headers['Cache-Control'] = 'public, max-age=86400';
      }
      res.writeHead(200, headers);
      res.end(data);
    });
  };

  // If the URL has a file extension, it's a static asset request
  if (hasFileExtension(requestPath)) {
    fs.stat(filePath, (err, stats) => {
      if (!err && stats.isFile()) {
        // Determine cache type: hashed assets contain a hash in the filename
        const fileName = path.basename(filePath);
        const isHashed = /[.-][a-f0-9]{8,}\./i.test(fileName); // e.g., index-abc123.js
        serveWithCache(res, filePath, isHashed ? 'hashed' : 'static');
      } else {
        // Missing static file – return 404, do NOT fall back to index.html
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
      }
    });
  } else {
    // No file extension – serve index.html (SPA fallback)
    serveWithCache(res, path.join(DIST_DIR, 'index.html'), 'html');
  }
});

server.listen(PORT, () => {
  console.log(`Frontend server running on port ${PORT}`);
});
