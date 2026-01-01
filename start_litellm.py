"""Load .env and start LiteLLM."""
import subprocess
import sys

from env_loader import load_env, get_database_url
from postgres_manager import PostgreSQLManager

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

    # Verify PostgreSQL is ready before starting LiteLLM
    print('[INFO] Verifying PostgreSQL is accepting connections...', flush=True)
    pg = PostgreSQLManager()
    if not pg.wait_for_ready(timeout=30):
        print('[ERROR] PostgreSQL is not accepting connections', flush=True)
        print('[ERROR] LiteLLM will fail to start without database access', flush=True)
        print('[ERROR] Check if PostgreSQL started correctly (see postgres/logfile)', flush=True)
        sys.exit(1)
    print('[OK] PostgreSQL is ready', flush=True)

print('[INFO] Starting LiteLLM...', flush=True)

# Start LiteLLM with environment variables loaded
# Note: We don't capture output so it streams to console in real-time
try:
    result = subprocess.run([
        'litellm',
        '--config', 'config.yaml',
        '--port', '11434',
        '--host', '127.0.0.1'
    ], env=env_vars)

    # Check if LiteLLM exited with an error
    if result.returncode != 0:
        print(f'[ERROR] LiteLLM exited with code {result.returncode}', flush=True)
        sys.exit(result.returncode)

except KeyboardInterrupt:
    print('[INFO] LiteLLM stopped', flush=True)
except FileNotFoundError:
    print('[ERROR] LiteLLM command not found. Is it installed?', flush=True)
    print('[ERROR] Try: pip install litellm[proxy]', flush=True)
    sys.exit(1)
except Exception as e:
    print(f'[ERROR] LiteLLM failed: {e}', flush=True)
    sys.exit(1)
