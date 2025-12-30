module.exports = {
  run: [
    {
      method: "fs.write",
      params: {
        path: "full_install.py",
        text: `# -*- coding: utf-8 -*-
import sys, os, subprocess, secrets

def run_command(cmd, desc=""):
    """Helper to run a command and print status."""
    if desc:
        print(f"[INFO] {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARNING] Command may have had issues: {result.stderr[:200]}")
    return result

print('='*60)
print('Virtual Model Emulator - Installation')
print('='*60)

# 1. INSTALL/UPGRADE DEPENDENCIES
print('\\n[1/2] Installing/Upgrading dependencies...')
run_command(f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip")
run_command(f'"{sys.executable}" -m pip install --upgrade litellm[proxy]', "Installing litellm[proxy]")
print('[OK] Dependencies installed.')

# 2. GENERATE CONFIG.YAML (if missing)
print('\\n[2/2] Checking configuration...')
config_file = 'config.yaml'
if os.path.exists(config_file):
    print('[OK] config.yaml already exists.')
else:
    master_key = 'sk-' + secrets.token_hex(16)
    config_content = f'''model_list: []

general_settings:
  master_key: {master_key}

litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''
    with open(config_file, 'w') as f:
        f.write(config_content)
    print(f'[OK] config.yaml generated with empty model_list.')

# 3. CREATE INSTALLATION MARKER
os.makedirs('env', exist_ok=True)
with open('env/.installed', 'w') as f:
    f.write('Installation completed successfully.')
print('[OK] Installation marker created.')

print('\\n' + '='*60)
print('INSTALLATION COMPLETE')
print('Wildcard providers will be added dynamically via /model/new API')
print('='*60)
`
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python full_install.py"
      }
    }
  ]
};
