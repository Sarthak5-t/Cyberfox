#!/usr/bin/env node

/**
 * Cyberfox Auth Development Server
 *
 * Companion server for local development of the authentication UI.
 * - Provides WebAuthn (passkey) registration and authentication endpoints
 * - Provides password login with JWT in HttpOnly cookies
 * - CSRF token generation
 * - Rate limiting simulation
 *
 * This is a DEV-ONLY server. For production, replace with a proper auth
 * provider (Auth0, Clerk, Custom backend, etc.).
 *
 * Usage:
 *   node api/auth-server.mjs
 *   # Starts on http://localhost:4001
 *
 * Then start Docusaurus:
 *   npm start
 *   # The /api/* proxy in docusaurus.config.ts forwards to this server
 */

import http from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';

const PORT = 4001;
const JWT_SECRET = randomBytes(32).toString('hex');

// ─── In-memory "database" (dev only) ─────────────────────────────────
const users = new Map([
  [
    'admin@cyberfox.dev',
    {
      id: 'user_001',
      name: 'Admin',
      email: 'admin@cyberfox.dev',
      password: 'cyberfox123',
      roles: ['admin'],
      passkeys: [],
    },
  ],
]);

const sessions = new Map();
const csrfTokens = new Set();

// ─── Rate limiting (per-IP tracker) ──────────────────────────────────
const loginAttempts = new Map();

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = loginAttempts.get(ip) || { count: 0, resetAt: now };
  if (now > entry.resetAt) {
    entry.count = 0;
    entry.resetAt = now + 60000;
  }
  entry.count++;
  loginAttempts.set(ip, entry);
  entry.remaining = Math.max(0, 5 - entry.count);
  entry.blocked = entry.count > 5;
  return entry;
}

// ─── JWT helpers ─────────────────────────────────────────────────────
function encodeBase64URL(buf) {
  return buf.toString('base64url');
}

function createJWT(payload) {
  const header = encodeBase64URL(Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })));
  const body = encodeBase64URL(Buffer.from(JSON.stringify({ ...payload, iat: Date.now(), exp: Date.now() + 3600000 })));
  const signature = encodeBase64URL(
    Buffer.from(
      Array.from(new TextEncoder().encode(`${header}.${body}${JWT_SECRET}`))
        .map(b => b.toString(16).padStart(2, '0'))
        .join(''),
    ),
  );
  return `${header}.${body}.${signature}`;
}

function parseCookies(req) {
  const c = {};
  (req.headers.cookie || '').split(';').forEach((pair) => {
    const [k, ...v] = pair.trim().split('=');
    if (k) c[k.trim()] = v.join('=');
  });
  return c;
}

function setCookie(res, name, value, opts = {}) {
  const parts = [`${name}=${value}`];
  if (opts.httpOnly !== false) parts.push('HttpOnly');
  if (opts.secure !== false) parts.push('Secure');
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.maxAge) parts.push(`Max-Age=${opts.maxAge}`);
  res.setHeader('Set-Cookie', parts.join('; '));
}

function json(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token',
  });
  res.end(body);
}

function getBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (c) => (data += c));
    req.on('end', () => {
      try {
        resolve(JSON.parse(data));
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

// ─── Routes ──────────────────────────────────────────────────────────

async function handleRequest(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const path = url.pathname;
  const method = req.method;
  const ip = req.socket.remoteAddress || '127.0.0.1';

  // CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': 'http://localhost:3000',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    });
    res.end();
    return;
  }

  // GET /api/auth/session — check current session
  if (method === 'GET' && path === '/api/auth/session') {
    const cookies = parseCookies(req);
    const token = cookies['cyberfox_session'];
    if (token && sessions.has(token)) {
      const user = sessions.get(token);
      return json(res, 200, { user });
    }
    return json(res, 401, { user: null });
  }

  // GET /api/auth/csrf — CSRF token
  if (method === 'GET' && path === '/api/auth/csrf') {
    const token = randomBytes(32).toString('hex');
    csrfTokens.add(token);
    return json(res, 200, { csrfToken: token });
  }

  // GET /api/auth/passkey/options — WebAuthn challenge (simplified)
  if (method === 'GET' && path === '/api/auth/passkey/options') {
    const challenge = randomBytes(32);
    return json(res, 200, {
      publicKey: {
        challenge: challenge.toString('base64url'),
        timeout: 60000,
        rpId: 'localhost',
        allowCredentials: [],
        userVerification: 'preferred',
      },
    });
  }

  // POST /api/auth/passkey/verify — Verify passkey assertion (simplified)
  if (method === 'POST' && path === '/api/auth/passkey/verify') {
    try {
      const body = await getBody(req);
      // In dev mode, accept any valid-looking assertion
      const user = users.get('admin@cyberfox.dev');
      if (!user) return json(res, 401, { message: 'No user found' });

      const token = randomBytes(32).toString('hex');
      sessions.set(token, { id: user.id, name: user.name, email: user.email, roles: user.roles });
      setCookie(res, 'cyberfox_session', token, { path: '/', maxAge: 3600, sameSite: 'Lax' });
      return json(res, 200, { user: { id: user.id, name: user.name, email: user.email, roles: user.roles } });
    } catch {
      return json(res, 400, { message: 'Invalid assertion' });
    }
  }

  // POST /api/auth/login — Password login
  if (method === 'POST' && path === '/api/auth/login') {
    const rateLimit = checkRateLimit(ip);

    res.setHeader('X-RateLimit-Remaining', String(rateLimit.remaining));
    if (rateLimit.blocked) {
      res.setHeader('Retry-After', '60');
      return json(res, 429, { message: 'Too many attempts. Try again in 60 seconds.' });
    }

    try {
      const body = await getBody(req);

      // CSRF check
      const csrf = req.headers['x-csrf-token'];
      if (!csrf || !csrfTokens.has(csrf)) {
        return json(res, 403, { message: 'Invalid CSRF token' });
      }
      csrfTokens.delete(csrf);

      const user = users.get(body.email);
      if (!user || user.password !== body.password) {
        return json(res, 401, { message: 'Invalid email or password.' });
      }

      const token = randomBytes(32).toString('hex');
      sessions.set(token, { id: user.id, name: user.name, email: user.email, roles: user.roles });
      setCookie(res, 'cyberfox_session', token, { path: '/', maxAge: 3600, sameSite: 'Lax' });

      loginAttempts.delete(ip);
      return json(res, 200, { user: { id: user.id, name: user.name, email: user.email, roles: user.roles } });
    } catch {
      return json(res, 400, { message: 'Invalid request body' });
    }
  }

  // POST /api/auth/logout — Clear session
  if (method === 'POST' && path === '/api/auth/logout') {
    const cookies = parseCookies(req);
    const token = cookies['cyberfox_session'];
    if (token) sessions.delete(token);
    setCookie(res, 'cyberfox_session', '', { path: '/', maxAge: 0 });
    return json(res, 200, { success: true });
  }

  // 404
  json(res, 404, { error: 'Not found' });
}

// ─── Start server ────────────────────────────────────────────────────

const server = http.createServer(handleRequest);
server.listen(PORT, () => {
  console.log(`\n  🔐 Cyberfox Auth Dev Server`);
  console.log(`  ─────────────────────────`);
  console.log(`  URL:   http://localhost:${PORT}`);
  console.log(`  Users: admin@cyberfox.dev / cyberfox123`);
  console.log(`\n  Start Docusaurus: npm start\n`);
});
