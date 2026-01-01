"""Load .env and start LiteLLM with Prisma setup."""
import subprocess
import sys
import os
import shutil

from env_loader import load_env, get_database_url

# Load .env file
print('[INFO] Loading .env file...', flush=True)
env_vars = load_env()

# Verify DATABASE_URL exists
database_url = get_database_url(env_vars)
print('[OK] DATABASE_URL loaded', flush=True)

# Generate Prisma client for PostgreSQL if prisma CLI is available
# NOTE: Prisma is a standalone binary, not a Python module
prisma_bin = shutil.which('prisma')

if prisma_bin and 'postgresql' in database_url.lower():
    print('[INFO] Generating Prisma client for PostgreSQL...', flush=True)

    try:
        # Run prisma generate - Prisma will find its own schema
        # when installed via pip, it knows where litellm's schema is
        result = subprocess.run([
            prisma_bin, 'generate'
        ], env=env_vars, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f'[WARNING] Prisma generate failed: {result.stderr}', flush=True)
            print('[INFO] LiteLLM will attempt to handle Prisma setup internally', flush=True)
        else:
            print('[OK] Prisma client generated', flush=True)

    except subprocess.TimeoutExpired:
        print('[WARNING] Prisma generate timed out', flush=True)
        print('[INFO] LiteLLM will attempt to handle Prisma setup internally', flush=True)
    except Exception as e:
        print(f'[WARNING] Prisma setup error: {e}', flush=True)
        print('[INFO] LiteLLM will attempt to handle Prisma setup internally', flush=True)
else:
    if not prisma_bin:
        print('[INFO] Prisma CLI not found in PATH, skipping generation', flush=True)
    print('[INFO] LiteLLM will handle Prisma setup internally', flush=True)

print('[INFO] Starting LiteLLM with PostgreSQL database...', flush=True)

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
