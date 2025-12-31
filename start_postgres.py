"""Start PostgreSQL server before running the app."""
import os
import subprocess
import time
import sys

print('[INFO] Starting PostgreSQL...', flush=True)

postgres_dir = 'postgres'
data_dir = os.path.join(postgres_dir, 'data')
bin_dir = os.path.join(postgres_dir, 'bin')
pg_ctl = os.path.join(bin_dir, 'pg_ctl.exe')

# Check if PostgreSQL is already running
try:
    result = subprocess.run(
        [pg_ctl, 'status', '-D', data_dir],
        capture_output=True,
        text=True,
        timeout=5
    )
    if 'server is running' in result.stdout:
        print('[OK] PostgreSQL already running', flush=True)
        sys.exit(0)
except Exception as e:
    print(f'[DEBUG] Status check: {e}', flush=True)

# Start PostgreSQL with -w flag to wait for startup
try:
    print('[INFO] Starting PostgreSQL server...', flush=True)
    result = subprocess.run([
        pg_ctl, 'start',
        '-w',  # Wait for startup to complete
        '-t', '30',  # Timeout after 30 seconds
        '-D', data_dir,
        '-l', 'postgres/logfile'
    ], capture_output=True, text=True, timeout=35)

    if result.returncode != 0:
        print(f'[ERROR] pg_ctl failed: {result.stderr}', flush=True)
        sys.exit(1)

    print('[OK] PostgreSQL started', flush=True)

except subprocess.TimeoutExpired:
    print('[ERROR] PostgreSQL startup timed out', flush=True)
    sys.exit(1)
except Exception as e:
    print(f'[ERROR] Failed to start: {e}', flush=True)
    sys.exit(1)

# Give it a moment to fully initialize
time.sleep(2)

# Create litellm database if it doesn't exist
createdb = os.path.join(bin_dir, 'createdb.exe')
try:
    print('[INFO] Creating litellm database...', flush=True)
    result = subprocess.run(
        [createdb, '-U', 'postgres', 'litellm'],
        capture_output=True,
        text=True,
        timeout=10
    )
    # Ignore error if database already exists
    if result.returncode != 0:
        if 'already exists' in result.stderr:
            print('[OK] Database already exists', flush=True)
        else:
            print(f'[WARN] createdb: {result.stderr}', flush=True)
    else:
        print('[OK] Database created', flush=True)
except Exception as e:
    print(f'[WARN] createdb failed: {e}', flush=True)

print('[OK] PostgreSQL ready', flush=True)
