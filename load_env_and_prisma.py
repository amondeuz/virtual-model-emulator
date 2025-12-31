"""Load .env and run prisma generate."""
import os
import subprocess
import sys

# Load .env file
env_file = '.env'
if not os.path.exists(env_file):
    print('[ERROR] .env file not found', flush=True)
    sys.exit(1)

# Parse .env and set environment variables
print('[INFO] Loading .env file...', flush=True)
with open(env_file, 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print('[ERROR] DATABASE_URL not found in .env', flush=True)
    sys.exit(1)

print(f'[OK] DATABASE_URL loaded: {database_url[:30]}...', flush=True)

# Run prisma generate
print('[INFO] Running prisma generate...', flush=True)
try:
    result = subprocess.run(
        ['prisma', 'generate'],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        print(f'[ERROR] prisma generate failed: {result.stderr}', flush=True)
        sys.exit(1)

    print('[OK] Prisma generated', flush=True)

except Exception as e:
    print(f'[ERROR] Failed to run prisma generate: {e}', flush=True)
    sys.exit(1)
