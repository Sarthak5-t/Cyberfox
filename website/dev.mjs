#!/usr/bin/env node
import http from 'node:http';
import { spawn } from 'node:child_process';

const AUTH_PORT = 4001;
const DOCUSAURUS_PORT = 3001;
const PROXY_PORT = 3000;

// ─── Start auth server ──────────────────────────────────────────────
const auth = spawn('node', ['api/auth-server.mjs'], {
  stdio: ['inherit', 'pipe', 'inherit'],
});

// ─── Start Docusaurus on 3001 ───────────────────────────────────────
const docusaurus = spawn('npx', ['docusaurus', 'start', '--no-open', '--port', String(DOCUSAURUS_PORT)], {
  stdio: ['inherit', 'pipe', 'inherit'],
});

// ─── Proxy: port 3000 → 3001 (everything) / 4001 (/api/*) ─────────
const proxy = http.createServer((req, res) => {
  const target = req.url.startsWith('/api/')
    ? { host: 'localhost', port: AUTH_PORT }
    : { host: 'localhost', port: DOCUSAURUS_PORT };

  const options = {
    hostname: target.host,
    port: target.port,
    path: req.url,
    method: req.method,
    headers: { ...req.headers },
  };

  // Remove host header to let the target server set it
  delete options.headers.host;

  const proxyReq = http.request(options, (proxyRes) => {
    // Fix CORS for auth API responses
    if (target.port === AUTH_PORT) {
      proxyRes.headers['access-control-allow-origin'] = '*';
      delete proxyRes.headers['access-control-allow-credentials'];
    }
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end(`Proxy error: ${err.message}`);
  });

  req.pipe(proxyReq);
});

// ─── WebSocket upgrade for Docusaurus HMR ──────────────────────────
proxy.on('upgrade', (req, socket, head) => {
  const target = { host: 'localhost', port: DOCUSAURUS_PORT };
  const proxyReq = http.request({
    hostname: target.host,
    port: target.port,
    path: req.url,
    method: 'GET',
    headers: req.headers,
  });
  proxyReq.on('upgrade', (proxyRes, proxySocket, proxyHead) => {
    socket.write(
      'HTTP/1.1 101 Switching Protocols\r\n' +
      'Upgrade: websocket\r\n' +
      'Connection: Upgrade\r\n' +
      '\r\n'
    );
    proxySocket.pipe(socket).pipe(proxySocket);
  });
  proxyReq.end();
});

proxy.listen(PROXY_PORT, () => {
  console.log(`\n  🚀 Cyberfox Dev Server`);
  console.log(`  ─────────────────────`);
  console.log(`  URL:    http://localhost:${PROXY_PORT}`);
  console.log(`  Auth:   http://localhost:${AUTH_PORT}`);
  console.log(`  Press Ctrl+C to stop\n`);
});

// ─── Cleanup ────────────────────────────────────────────────────────
function cleanup() {
  auth.kill();
  docusaurus.kill();
  proxy.close();
  process.exit();
}
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
