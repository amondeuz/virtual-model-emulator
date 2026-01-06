module.exports = {
  run: [
    {
      method: "fs.write",
      params: {
        path: "full_install.py",
        text: `# -*- coding: utf-8 -*-
"""
Virtual Model Emulator v2.2.0 - Simplified Installation
Only installs LiteLLM SDK (no proxy, no PostgreSQL needed).
"""
import sys
import os
import subprocess
import secrets

def run_command(cmd, desc=""):
    """Helper to run a command and print status."""
    if desc:
        print(f"[INFO] {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARNING] Command may have had issues: {result.stderr[:200]}")
    return result

print('='*60)
print('Virtual Model Emulator v2.2.0 - Installation')
print('SDK Mode (No Proxy Required)')
print('='*60)

# 1. INSTALL DEPENDENCIES
print('\\n[1/3] Installing dependencies...')
run_command(f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip")

# Install only LiteLLM SDK (not proxy extras)
result = run_command(f'"{sys.executable}" -m pip install --upgrade "litellm>=1.10.0"', "Installing litellm>=1.10.0")
if result.returncode != 0:
    # Try with --break-system-packages for some Linux systems
    run_command(f'"{sys.executable}" -m pip install --break-system-packages --upgrade "litellm>=1.10.0"', "Installing litellm>=1.10.0 (retry)")
print('[OK] Dependencies installed.')

# 2. GENERATE .ENV FILE (minimal config)
print('\\n[2/3] Checking configuration...')
env_file = '.env'
if not os.path.exists(env_file):
    env_content = f'''# Virtual Model Emulator Configuration
# API Server port
API_SERVER_PORT=8775
'''
    with open(env_file, 'w') as f:
        f.write(env_content)
    print('[OK] .env file generated.')
else:
    print('[OK] .env file already exists.')

# 3. CREATE DIRECTORIES AND INSTALLATION MARKER
print('\\n[3/3] Finalizing installation...')
os.makedirs('config', exist_ok=True)
os.makedirs('public', exist_ok=True)
os.makedirs('env', exist_ok=True)
with open('env/.installed', 'w') as f:
    f.write('Installation completed successfully (SDK mode).')
print('[OK] Installation marker created.')

print('\\n' + '='*60)
print('INSTALLATION COMPLETE')
print('')
print('This version uses LiteLLM SDK directly:')
print('  - No PostgreSQL database needed')
print('  - No LiteLLM proxy server needed')
print('  - Faster startup, simpler architecture')
print('')
print('Just run "Start" to launch the emulator!')
print('='*60)
`
      }
    },
    {
      method: "fs.write",
      params: {
        path: "config.yaml",
        text: "# Virtual Model Emulator Configuration\n# Master key will be auto-generated on first run\n# Do not share this file - it contains your encryption key\n"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python full_install.py"
      }
    },
    {
      method: "fs.rm",
      params: {
        path: "full_install.py"
      }
    }
  ]
};
