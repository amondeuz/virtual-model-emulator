"""Load .env and start LiteLLM."""
import subprocess
import sys

from env_loader import load_env, get_database_url

# Load .env file
print('[INFO] Loading .env file...', flush=True)
env_vars = load_env()

# Verify DATABASE_URL exists
database_url = get_database_url(env_vars)
print('[OK] DATABASE_URL loaded', flush=True)

# Prisma setup is handled automatically by LiteLLM on first startup
if 'postgresql' in database_url.lower():
    print('[INFO] Using PostgreSQL database', flush=True)
    print('[INFO] Prisma client will be generated automatically by LiteLLM', flush=True)

print('[INFO] Starting LiteLLM...', flush=True)

# Start LiteLLM with environment variables loaded
try:
    subprocess.run([
        'litellm',
        '--config', 'config.yaml',
        '--port', '11434',
        '--host', '127.0.0.1'
    ], env=env_vars)
except KeyboardInterrupt:
    print('[INFO] LiteLLM stopped', flush=True)
except Exception as e:
    print(f'[ERROR] LiteLLM failed: {e}', flush=True)
    sys.exit(1)
