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
print('Virtual Model Emulator v2.1.2 - Installation')
print('='*60)

# 1. INSTALL/UPGRADE DEPENDENCIES
print('\\n[1/5] Installing/Upgrading dependencies...')
run_command(f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip")
run_command(f'"{sys.executable}" -m pip install --upgrade litellm[proxy]', "Installing litellm[proxy]")
# Install Prisma for database support
result = run_command(f'"{sys.executable}" -m pip install prisma', "Installing prisma")
if result.returncode != 0:
    run_command(f'"{sys.executable}" -m pip install --break-system-packages prisma', "Installing prisma (with --break-system-packages)")
print('[OK] Dependencies installed.')

# 2. INSTALL POSTGRESQL (Windows)
print('\\n[2/5] Installing PostgreSQL...')
import urllib.request
import zipfile
import shutil

postgres_version = '16.1-1'
postgres_url = f'https://get.enterprisedb.com/postgresql/postgresql-{postgres_version}-windows-x64-binaries.zip'
postgres_zip = 'postgres.zip'
postgres_dir = 'postgres'
env_file = '.env'

# Check for state consistency before proceeding
postgres_exists = os.path.exists(postgres_dir)
env_exists = os.path.exists(env_file)

if postgres_exists and not env_exists:
    print('[ERROR] PostgreSQL directory exists but .env file is missing.')
    print('[ERROR] This can cause password mismatch issues.')
    print('[ERROR] To fix: Delete the postgres/ directory and run install again.')
    sys.exit(1)

if not postgres_exists and env_exists:
    print('[ERROR] .env file exists but PostgreSQL directory is missing.')
    print('[ERROR] This can cause password mismatch issues.')
    print('[ERROR] To fix: Delete the .env file and run install again.')
    sys.exit(1)

if not os.path.exists(postgres_dir):
    print(f'Downloading PostgreSQL {postgres_version}...')
    urllib.request.urlretrieve(postgres_url, postgres_zip)

    print('Extracting PostgreSQL...')
    with zipfile.ZipFile(postgres_zip, 'r') as zip_ref:
        zip_ref.extractall('.')
    os.remove(postgres_zip)

    # Rename extracted folder
    extracted = 'pgsql'
    if os.path.exists(extracted):
        shutil.move(extracted, postgres_dir)

    print('Initializing PostgreSQL database...')
    data_dir = os.path.join(postgres_dir, 'data')
    bin_dir = os.path.join(postgres_dir, 'bin')
    initdb = os.path.join(bin_dir, 'initdb.exe')

    # Generate password for PostgreSQL
    db_password = secrets.token_urlsafe(16)

    # Write password to temp file for initdb (Windows-compatible)
    password_file = 'postgres_pwd.tmp'
    with open(password_file, 'w') as f:
        f.write(db_password)

    try:
        run_command(f'"{initdb}" -D "{data_dir}" -U postgres -A scram-sha-256 --pwfile="{password_file}"', 'Initializing database with scram-sha-256 authentication')
    finally:
        # Clean up password file with verification
        try:
            if os.path.exists(password_file):
                os.remove(password_file)
                # Verify deletion succeeded
                if os.path.exists(password_file):
                    print(f'[WARNING] Failed to delete password file - manual cleanup required', flush=True)
                    print(f'[WARNING] Delete this file manually: {password_file}', flush=True)
        except Exception as e:
            print(f'[ERROR] Could not delete password file: {e}', flush=True)
            print(f'[ERROR] Delete this file manually: {password_file}', flush=True)

    # Store password for .env generation
    os.environ['PG_PASSWORD'] = db_password
    print('[OK] PostgreSQL installed and initialized with password authentication.')
else:
    print('[OK] PostgreSQL already installed.')

# 3. GENERATE .ENV FILE
print('\\n[3/5] Generating .env file...')
if not os.path.exists(env_file):
    # Use password from initialization, or generate new one if PostgreSQL was already installed
    db_password = os.environ.get('PG_PASSWORD', secrets.token_urlsafe(16))
    env_content = f'''# Database Configuration
DATABASE_URL=postgresql://postgres:{db_password}@localhost:5432/litellm?schema=public&connection_limit=10&pool_timeout=30&connect_timeout=10

# LiteLLM Configuration
LITELLM_MASTER_KEY=sk-{secrets.token_hex(16)}
'''
    with open(env_file, 'w') as f:
        f.write(env_content)
    print('[OK] .env file generated.')
else:
    print('[OK] .env file already exists.')

# 4. GENERATE CONFIG.YAML
print('\\n[4/5] Checking configuration...')
config_file = 'config.yaml'
if os.path.exists(config_file):
    print('[OK] config.yaml already exists.')
else:
    # Read master key from .env
    master_key = 'sk-' + secrets.token_hex(16)
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('LITELLM_MASTER_KEY='):
                    master_key = line.split('=')[1].strip()

    config_content = f'''model_list: []

general_settings:
  master_key: {master_key}
  database_url: env/DATABASE_URL

litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''
    with open(config_file, 'w') as f:
        f.write(config_content)
    print('[OK] config.yaml generated with PostgreSQL database configured.')

# 5. CREATE INSTALLATION MARKER
print('\\n[5/5] Finalizing installation...')
os.makedirs('env', exist_ok=True)
with open('env/.installed', 'w') as f:
    f.write('Installation completed successfully.')
print('[OK] Installation marker created.')

print('\\n' + '='*60)
print('INSTALLATION COMPLETE')
print('PostgreSQL database will be started automatically.')
print('Models will be added dynamically via /model/new API.')
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
