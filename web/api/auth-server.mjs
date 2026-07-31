#!/usr/bin/env node
import http from 'node:http'
import { randomBytes } from 'node:crypto'

const PORT = 4001
const JWT_SECRET = randomBytes(32).toString('hex')
const ORIGIN = 'http://localhost:5173'

const users = new Map([
  ['admin@cyberfox.dev', {
    id: 'user_001',
    name: 'Admin',
    email: 'admin@cyberfox.dev',
    password: 'cyberfox123',
    roles: ['admin'],
    passkeys: [],
  }],
])

const sessions = new Map()
const csrfTokens = new Set()

const loginAttempts = new Map()

function checkRateLimit(ip) {
  const now = Date.now()
  const entry = loginAttempts.get(ip) || { count: 0, resetAt: now + 60000 }
  if (now > entry.resetAt) {
    entry.count = 0
    entry.resetAt = now + 60000
  }
  entry.count++
  loginAttempts.set(ip, entry)
  entry.remaining = Math.max(0, 5 - entry.count)
  entry.blocked = entry.count > 5
  return entry
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': ORIGIN,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Vary': 'Origin',
  }
}

function json(res, status, data) {
  const body = JSON.stringify(data)
  res.writeHead(status, {
    'Content-Type': 'application/json',
    ...corsHeaders(),
  })
  res.end(body)
}

function parseCookies(req) {
  const c = {}
  ;(req.headers.cookie || '').split(';').forEach((pair) => {
    const [k, ...v] = pair.trim().split('=')
    if (k) c[k.trim()] = v.join('=')
  })
  return c
}

function setCookie(res, name, value, opts = {}) {
  const parts = [`${name}=${value}`]
  if (opts.httpOnly !== false) parts.push('HttpOnly')
  parts.push('Secure')
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`)
  if (opts.path) parts.push(`Path=${opts.path}`)
  if (opts.maxAge) parts.push(`Max-Age=${opts.maxAge}`)
  res.setHeader('Set-Cookie', parts.join('; '))
}

async function getBody(req) {
  return new Promise((resolve, reject) => {
    let data = ''
    req.on('data', (c) => (data += c))
    req.on('end', () => {
      try { resolve(JSON.parse(data)) }
      catch { reject(new Error('Invalid JSON')) }
    })
    req.on('error', reject)
  })
}

async function handleRequest(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`)
  const path = url.pathname
  const method = req.method
  const ip = req.socket.remoteAddress || '127.0.0.1'

  if (method === 'OPTIONS') {
    res.writeHead(204, corsHeaders())
    res.end()
    return
  }

  // GET /api/auth/me
  if (method === 'GET' && path === '/api/auth/me') {
    const cookies = parseCookies(req)
    const token = cookies['cyberfox_session']
    if (token && sessions.has(token)) {
      const user = sessions.get(token)
      return json(res, 200, user)
    }
    return json(res, 401, { error: 'unauthenticated' })
  }

  // GET /api/auth/csrf
  if (method === 'GET' && path === '/api/auth/csrf') {
    const token = randomBytes(32).toString('hex')
    csrfTokens.add(token)
    return json(res, 200, { csrfToken: token })
  }

  // GET /api/auth/passkey/start
  if (method === 'GET' && path === '/api/auth/passkey/start') {
    const challenge = randomBytes(32)
    return json(res, 200, {
      publicKey: {
        challenge: challenge.toString('base64url'),
        timeout: 60000,
        rpId: 'localhost',
        allowCredentials: [],
        userVerification: 'preferred',
      },
    })
  }

  // POST /api/auth/passkey/verify
  if (method === 'POST' && path === '/api/auth/passkey/verify') {
    try {
      const body = await getBody(req)
      const user = users.get('admin@cyberfox.dev')
      if (!user) return json(res, 401, { message: 'No user found' })

      const token = randomBytes(32).toString('hex')
      sessions.set(token, { user_id: user.id, email: user.email, display_name: user.name, roles: user.roles, provider: 'passkey', org_id: '', expires_at: Date.now() + 3600000 })
      setCookie(res, 'cyberfox_session', token, { path: '/', maxAge: 3600, sameSite: 'Lax' })
      return json(res, 200, { user: { user_id: user.id, email: user.email, display_name: user.name, roles: user.roles, provider: 'passkey', org_id: '', expires_at: Date.now() + 3600000 } })
    } catch {
      return json(res, 400, { message: 'Invalid assertion' })
    }
  }

  // POST /api/auth/login
  if (method === 'POST' && path === '/api/auth/login') {
    const rateLimit = checkRateLimit(ip)
    res.setHeader('X-RateLimit-Remaining', String(rateLimit.remaining))
    if (rateLimit.blocked) {
      res.setHeader('Retry-After', '60')
      return json(res, 429, { message: 'Too many attempts. Try again in 60 seconds.' })
    }

    try {
      const body = await getBody(req)
      const csrf = req.headers['x-csrf-token']
      if (!csrf || !csrfTokens.has(csrf)) {
        return json(res, 403, { message: 'Invalid CSRF token' })
      }
      csrfTokens.delete(csrf)

      const user = users.get(body.email)
      if (!user || user.password !== body.password) {
        return json(res, 401, { message: 'Invalid email or password.' })
      }

      const token = randomBytes(32).toString('hex')
      sessions.set(token, { user_id: user.id, email: user.email, display_name: user.name, roles: user.roles, provider: 'password', org_id: '', expires_at: Date.now() + 3600000 })
      setCookie(res, 'cyberfox_session', token, { path: '/', maxAge: 3600, sameSite: 'Lax' })
      loginAttempts.delete(ip)
      return json(res, 200, { user: { user_id: user.id, email: user.email, display_name: user.name, roles: user.roles, provider: 'password', org_id: '', expires_at: Date.now() + 3600000 } })
    } catch {
      return json(res, 400, { message: 'Invalid request body' })
    }
  }

  // POST /auth/logout
  if (method === 'POST' && path === '/auth/logout') {
    const cookies = parseCookies(req)
    const token = cookies['cyberfox_session']
    if (token) sessions.delete(token)
    setCookie(res, 'cyberfox_session', '', { path: '/', maxAge: 0 })
    return json(res, 200, { success: true })
  }

  json(res, 404, { error: 'Not found' })
}

const server = http.createServer(handleRequest)
server.listen(PORT, () => {
  console.log(`\n  🔐 Cyberfox Auth Dev Server`)
  console.log(`  ─────────────────────────`)
  console.log(`  URL:   http://localhost:${PORT}`)
  console.log(`  Users: admin@cyberfox.dev / cyberfox123`)
  console.log(`\n  CORS origin: ${ORIGIN}\n`)
})
