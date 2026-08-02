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

// Start Python backend with the auth gate forced on, so the loopback bind
// (and the Vite dev port proxying to it) requires login.
const backend = spawn(
  'python', ['-m', 'cyberfox_cli.main', 'dashboard', '--no-open'],
  {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      VIRTUAL_ENV: resolve(ROOT, 'venv'),
      PATH: `${resolve(ROOT, 'venv/bin')}:${process.env.PATH}`,
      CYBERFOX_DASHBOARD_FORCE_AUTH: '1',
    },
  },
)
backend.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`))
backend.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`))
backend.on('exit', (code) => log('backend', `exited with code ${code}`))

// Wait for the backend to come up, then start Vite
setTimeout(() => {
  const vite = spawn('npx', ['vite'], {
    cwd: __dirname,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: true,
  })
  vite.stdout.on('data', (d) => process.stdout.write(`[vite] ${d}`))
  vite.stderr.on('data', (d) => process.stderr.write(`[vite] ${d}`))
  vite.on('exit', (code) => log('vite', `exited with code ${code}`))

  process.on('SIGINT', () => { vite.kill(); backend.kill(); process.exit() })
  process.on('SIGTERM', () => { vite.kill(); backend.kill(); process.exit() })
}, 8000)

log('dev', 'Starting Cyberfox dev environment...')
log('dev', '  Backend: http://localhost:9119 (auth gate forced on)')
log('dev', '  Vite:    http://localhost:5173')
log('dev', '  Press Ctrl+C to stop all services')

process.on('SIGINT', () => { backend.kill(); process.exit() })
process.on('SIGTERM', () => { backend.kill(); process.exit() })
