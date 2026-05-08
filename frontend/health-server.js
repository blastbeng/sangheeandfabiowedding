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

  // Console log for all other requests (like serve does)
  console.log(`${new Date().toISOString()} ${req.method} ${url}`);

  // Try to serve exact file
  const filePath = path.join(DIST_DIR, url === '/' ? 'index.html' : url);
  fs.stat(filePath, (err, stats) => {
    if (!err && stats.isFile()) {
      serveStatic(res, filePath);
    } else {
      // SPA fallback: serve index.html for any non-file route
      serveStatic(res, path.join(DIST_DIR, 'index.html'));
    }
  });
});

server.listen(PORT, () => {
  console.log(`Frontend server running on port ${PORT}`);
});
