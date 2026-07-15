#!/usr/bin/env node

const { execSync } = require('child_process');
const os = require('os');

const platform = os.platform();
const version = '1.2.9';

console.log('📦 Installing GlanceWatch v' + version + '...');
console.log('Platform:', platform);

try {
  // Check if Python is available
  let pythonCmd = 'python3';
  try {
    execSync('python3 --version', { stdio: 'ignore' });
  } catch {
    try {
      execSync('python --version', { stdio: 'ignore' });
      pythonCmd = 'python';
    } catch {
      console.error('❌ Python 3.8+ is required but not found.');
      console.error('Please install Python from https://www.python.org/downloads/');
      process.exit(1);
    }
  }

  console.log('✓ Python found');

  // Install glancewatch via pip
  console.log('Installing glancewatch via pip...');
  execSync(`${pythonCmd} -m pip install --upgrade pip`, { stdio: 'inherit' });
  execSync(`${pythonCmd} -m pip install glancewatch==${version}`, { stdio: 'inherit' });

  console.log('✅ GlanceWatch v' + version + ' installed successfully!');
  console.log('');
  console.log('To start GlanceWatch, run:');
  console.log('  npx glancewatch');
  console.log('  or');
  console.log('  glancewatch (if installed globally)');
  console.log('');
  console.log('Web UI: http://localhost:8765');
  console.log('API Docs: http://localhost:8765/docs');
  console.log('');
} catch (error) {
  console.error('❌ Installation failed:', error.message);
  process.exit(1);
}
