"""Load .env and start LiteLLM."""
import subprocess
import sys
import os

from env_loader import load_env, get_database_url

# Load .env file
print('[INFO] Loading .env file...', flush=True)
env_vars = load_env()

# Verify DATABASE_URL exists
database_url = get_database_url(env_vars)
print('[OK] DATABASE_URL loaded', flush=True)

# Generate Prisma client for PostgreSQL
# NOTE: LiteLLM only auto-generates Prisma for SQLite, not PostgreSQL
print('[INFO] Generating Prisma client...', flush=True)
try:
    import litellm
    litellm_dir = os.path.dirname(litellm.__file__)
    schema_path = os.path.join(litellm_dir, 'proxy', 'prisma', 'schema.prisma')

    if os.path.exists(schema_path):
        result = subprocess.run([
            sys.executable, '-m', 'prisma', 'generate',
            '--schema', schema_path
        ], env=env_vars, capture_output=True, text=True)

        if result.returncode != 0:
            print(f'[WARNING] Prisma generate failed: {result.stderr}', flush=True)
            # Continue anyway - LiteLLM may handle this internally
        else:
            print('[OK] Prisma client generated', flush=True)
    else:
        print('[WARNING] Prisma schema not found, skipping generation', flush=True)
except ImportError:
    print('[WARNING] Could not import litellm for Prisma setup', flush=True)
except Exception as e:
    print(f'[WARNING] Prisma generation error: {e}', flush=True)

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
