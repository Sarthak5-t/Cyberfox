#!/usr/bin/env node
import { spawn } from 'node:child_process';

const DOCUSAURUS_PORT = 3000;

const docusaurus = spawn('npx', ['docusaurus', 'start', '--no-open', '--port', String(DOCUSAURUS_PORT)], {
  stdio: ['inherit', 'inherit', 'inherit'],
});

function cleanup() {
  docusaurus.kill();
  process.exit();
}
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
