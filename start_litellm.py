"""Load .env and start LiteLLM."""
import os
import subprocess
import sys

# Load .env file
env_file = '.env'
if not os.path.exists(env_file):
    print('[ERROR] .env file not found', flush=True)
    sys.exit(1)

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

print('[INFO] Starting LiteLLM with PostgreSQL database...', flush=True)

# Start LiteLLM with environment variables loaded
try:
    subprocess.run([
        'litellm',
        '--config', 'config.yaml',
        '--port', '11434',
        '--host', '127.0.0.1'
    ], env=os.environ.copy())
except KeyboardInterrupt:
    print('[INFO] LiteLLM stopped', flush=True)
except Exception as e:
    print(f'[ERROR] LiteLLM failed: {e}', flush=True)
    sys.exit(1)
