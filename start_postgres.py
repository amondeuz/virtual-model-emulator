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

# Start PostgreSQL
try:
    result = subprocess.run([
        pg_ctl, 'start',
        '-D', data_dir,
        '-l', 'postgres/logfile',
        '-o', '-p 5432'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode != 0:
        print(f'[ERROR] pg_ctl failed: {result.stderr}', flush=True)
        sys.exit(1)
        
except Exception as e:
    print(f'[ERROR] Failed to start: {e}', flush=True)
    sys.exit(1)

# Wait for PostgreSQL to be ready
print('[INFO] Waiting for PostgreSQL to be ready...', flush=True)
time.sleep(3)

# Create litellm database if it doesn't exist
createdb = os.path.join(bin_dir, 'createdb.exe')
try:
    result = subprocess.run(
        [createdb, '-U', 'postgres', 'litellm'],
        capture_output=True,
        text=True,
        timeout=10
    )
    # Ignore error if database already exists
    if result.returncode != 0 and 'already exists' not in result.stderr:
        print(f'[WARN] createdb: {result.stderr}', flush=True)
except Exception as e:
    print(f'[WARN] createdb failed: {e}', flush=True)

print('[OK] PostgreSQL ready', flush=True)
