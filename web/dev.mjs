#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')

function log(tag, msg) {
  const ts = new Date().toLocaleTimeString()
  console.log(`[${ts}] [${tag}] ${msg}`)
}

// Start auth server
const auth = spawn('node', ['api/auth-server.mjs'], {
  cwd: __dirname,
  stdio: ['ignore', 'pipe', 'pipe'],
})
auth.stdout.on('data', (d) => process.stdout.write(`[auth] ${d}`))
auth.stderr.on('data', (d) => process.stderr.write(`[auth] ${d}`))
auth.on('exit', (code) => log('auth', `exited with code ${code}`))

// Wait 2s, then start Python backend
const backend = spawn(
  'python', ['-m', 'cyberfox_cli.main', 'dashboard', '--no-open'],
  {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, VIRTUAL_ENV: resolve(ROOT, 'venv'), PATH: `${resolve(ROOT, 'venv/bin')}:${process.env.PATH}` },
  },
)
backend.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`))
backend.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`))
backend.on('exit', (code) => log('backend', `exited with code ${code}`))

// Wait for auth + backend, then start Vite
setTimeout(() => {
  const vite = spawn('npx', ['vite'], {
    cwd: __dirname,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: true,
  })
  vite.stdout.on('data', (d) => process.stdout.write(`[vite] ${d}`))
  vite.stderr.on('data', (d) => process.stderr.write(`[vite] ${d}`))
  vite.on('exit', (code) => log('vite', `exited with code ${code}`))

  process.on('SIGINT', () => { vite.kill(); backend.kill(); auth.kill(); process.exit() })
  process.on('SIGTERM', () => { vite.kill(); backend.kill(); auth.kill(); process.exit() })
}, 8000)

log('dev', 'Starting Cyberfox dev environment...')
log('dev', '  Auth:    http://localhost:4001')
log('dev', '  Backend: http://localhost:9119')
log('dev', '  Vite:    http://localhost:5173')
log('dev', '  Press Ctrl+C to stop all services')

process.on('SIGINT', () => { backend.kill(); auth.kill(); process.exit() })
process.on('SIGTERM', () => { backend.kill(); auth.kill(); process.exit() })
