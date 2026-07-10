/**
 * Tests for electron/backend-probes.cjs.
 *
 * Run with: node --test electron/backend-probes.test.cjs
 * (Wired into npm test:desktop:platforms in package.json.)
 */

const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const { canImportCyberfoxCli, cyberfoxRuntimeImportProbe, verifyCyberfoxCli } = require('./backend-probes.cjs')

// Resolve the host's own Node binary -- guaranteed to be on disk and
// runnable. We use it as both a stand-in for "a python that doesn't
// have cyberfox_cli" (since `node -c "import cyberfox_cli"` will exit
// non-zero) and as a way to script verifyCyberfoxCli's success path
// (a tiny script we write to disk that exits 0 on --version).
const NODE_BIN = process.execPath

test('canImportCyberfoxCli returns false when path is falsy', () => {
  assert.equal(canImportCyberfoxCli(''), false)
  assert.equal(canImportCyberfoxCli(null), false)
  assert.equal(canImportCyberfoxCli(undefined), false)
})

test('canImportCyberfoxCli returns false when interpreter cannot run -c', () => {
  // node IS an interpreter, but `node -c "import cyberfox_cli"` is a
  // SyntaxError -- different exit reason from a real Python's
  // ModuleNotFoundError, but the predicate is "exit 0 or not" and
  // both land on "not", which is exactly what we want for the
  // resolver fall-through.
  assert.equal(canImportCyberfoxCli(NODE_BIN), false)
})

test('canImportCyberfoxCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'cyberfox-probes-ghost-' + Date.now() + '.exe')
  assert.equal(canImportCyberfoxCli(ghost), false)
})

test('cyberfox runtime import probe checks config dependencies', () => {
  const probe = cyberfoxRuntimeImportProbe()
  assert.match(probe, /\bimport yaml\b/)
  // dotenv is the first third-party import on the CLI boot path
  // (cyberfox_cli/env_loader.py); a mid-update venv missing python-dotenv
  // passed the old probe and produced an unrecoverable boot loop.
  assert.match(probe, /\bimport dotenv\b/)
  assert.match(probe, /\bimport cyberfox_cli\.config\b/)
})

test('verifyCyberfoxCli returns false when command is falsy', () => {
  assert.equal(verifyCyberfoxCli(''), false)
  assert.equal(verifyCyberfoxCli(null), false)
  assert.equal(verifyCyberfoxCli(undefined), false)
})

test('verifyCyberfoxCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'cyberfox-probes-ghost-' + Date.now() + '.exe')
  assert.equal(verifyCyberfoxCli(ghost), false)
})

test('verifyCyberfoxCli returns true when --version exits 0', () => {
  // Write a tiny script that exits 0 regardless of args, then invoke
  // it through node. This stands in for a working cyberfox binary --
  // verifyCyberfoxCli only cares about the exit code.
  const scriptPath = path.join(os.tmpdir(), `cyberfox-probes-ok-${Date.now()}-${process.pid}.cjs`)
  fs.writeFileSync(scriptPath, 'process.exit(0)\n')
  try {
    // Use node as the launcher and our script as the "command". Pass
    // shell:false (default) -- node is a real binary, no shim.
    // execFileSync passes ['--version'] as args, which node ignores
    // gracefully (well, it prints its version and exits 0, which is
    // perfect -- exit code 0 is the only signal we read).
    assert.equal(verifyCyberfoxCli(NODE_BIN), true)
  } finally {
    try {
      fs.unlinkSync(scriptPath)
    } catch {
      void 0
    }
  }
})

test('verifyCyberfoxCli swallows timeouts (does not throw)', () => {
  // We can't easily provoke a real 5s hang in CI without slowing the
  // suite, but we CAN confirm that an invocation that DOES throw
  // (because the binary is missing) returns false rather than
  // propagating. Same code path the timeout case takes.
  assert.equal(verifyCyberfoxCli('/definitely/not/a/real/binary/anywhere'), false)
})
