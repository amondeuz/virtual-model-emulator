"""Start PostgreSQL server before running the app."""
import os
import subprocess
import time
import sys

postgres_dir = 'postgres'
data_dir = os.path.join(postgres_dir, 'data')
bin_dir = os.path.join(postgres_dir, 'bin')
postgres_exe = os.path.join(bin_dir, 'postgres.exe')
pg_ctl = os.path.join(bin_dir, 'pg_ctl.exe')

# Check if PostgreSQL directory exists
if not os.path.exists(postgres_dir):
    print('[ERROR] PostgreSQL not installed. Run install first.')
    sys.exit(1)

# Check if PostgreSQL is already running
try:
    result = subprocess.run(
        [pg_ctl, 'status', '-D', data_dir],
        capture_output=True,
        text=True
    )
    if 'server is running' in result.stdout:
        print('[INFO] PostgreSQL already running')
        print('[OK] PostgreSQL ready')
        sys.exit(0)
except Exception as e:
    print(f'[INFO] Checking PostgreSQL status: {e}')

# Start PostgreSQL
print('[INFO] Starting PostgreSQL...')
result = subprocess.run([
    pg_ctl, 'start',
    '-D', data_dir,
    '-l', os.path.join(postgres_dir, 'logfile'),
    '-o', '-p 5432'
], capture_output=True, text=True)

if result.returncode != 0:
    print(f'[WARNING] pg_ctl start output: {result.stderr}')

# Wait for PostgreSQL to be ready
time.sleep(3)

# Create litellm database if it doesn't exist
createdb = os.path.join(bin_dir, 'createdb.exe')
result = subprocess.run(
    [createdb, '-U', 'postgres', 'litellm'],
    capture_output=True,
    text=True
)
if result.returncode == 0:
    print('[INFO] Created litellm database')
elif 'already exists' in result.stderr:
    print('[INFO] litellm database already exists')

print('[OK] PostgreSQL ready')
