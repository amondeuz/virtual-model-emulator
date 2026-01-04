"""Load .env and start LiteLLM with proper error handling."""
import os
import subprocess
import sys
import time
import socket

from env_loader import load_env, get_database_url
from postgres_manager import PostgreSQLManager


def is_litellm_ready(host='127.0.0.1', port=None, timeout=30):
    """Check if LiteLLM is listening on the port.
    
    Args:
        host: LiteLLM host
        port: LiteLLM port (as string or int)
        timeout: Maximum seconds to wait
    
    Returns:
        bool: True if LiteLLM is responding to connections
    """
    if port is None:
        return False
    
    port = int(port)
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:  # Connection successful
                print(f'[OK] LiteLLM is listening on {host}:{port}', flush=True)
                return True
        except Exception:
            pass
        
        time.sleep(0.5)
    
    return False


def generate_prisma_client():
    """Generate Prisma client from litellm_proxy_extras package directory.
    
    CRITICAL: The Prisma schema is inside the litellm_proxy_extras package,
    not in the app directory. We must run `prisma generate` from that directory.
    
    Returns:
        bool: True if successful, False if failed
    """
    print('[INFO] Generating Prisma client...', flush=True)
    
    # Find litellm_proxy_extras package location
    try:
        import litellm_proxy_extras
        package_dir = litellm_proxy_extras.__path__[0]
        print(f'[INFO] Found litellm_proxy_extras at: {package_dir}', flush=True)
    except ImportError:
        print('[ERROR] litellm_proxy_extras not found - LiteLLM may not be properly installed', flush=True)
        return False
    except Exception as e:
        print(f'[ERROR] Failed to find litellm_proxy_extras: {e}', flush=True)
        return False
    
    # Run prisma generate from that directory
    try:
        print('[INFO] Running prisma generate...', flush=True)
        result = subprocess.run(
            [sys.executable, '-m', 'prisma', 'generate'],
            cwd=package_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print('[OK] Prisma client generated successfully', flush=True)
            return True
        else:
            print(f'[ERROR] prisma generate failed: {result.stderr[:500]}', flush=True)
            return False
            
    except subprocess.TimeoutExpired:
        print('[ERROR] prisma generate timed out (>60 seconds)', flush=True)
        return False
    except Exception as e:
        print(f'[ERROR] prisma generate error: {e}', flush=True)
        return False


def main():
    # Load .env file
    print('[INFO] Loading .env file...', flush=True)
    env_vars = load_env()

    # Verify DATABASE_URL exists
    database_url = get_database_url(env_vars)
    print('[OK] DATABASE_URL loaded', flush=True)
    # Fix config.yaml to use actual DATABASE_URL instead of placeholder
    from pathlib import Path
    config_file = Path(__file__).parent / 'config.yaml'
    if config_file.exists():
        content = config_file.read_text()
        # Replace the placeholder with actual database URL
        content = content.replace('database_url: env/DATABASE_URL', f'database_url: {database_url}')
        config_file.write_text(content)
        print('[OK] Updated config.yaml with DATABASE_URL', flush=True)

    # Get LiteLLM port from .env (defaults to 11435)
    litellm_port = env_vars.get('LITELLM_PORT', '11435')
    print(f'[INFO] Using LiteLLM port {litellm_port}', flush=True)

    # PostgreSQL verification
    if 'postgresql' in database_url.lower():
        print('[INFO] Using PostgreSQL database', flush=True)
        print('[INFO] Verifying PostgreSQL is accepting connections...', flush=True)
        pg = PostgreSQLManager()
        if not pg.wait_for_ready(timeout=30):
            print('[ERROR] PostgreSQL is not accepting connections', flush=True)
            print('[ERROR] LiteLLM will fail to start without database access', flush=True)
            print('[ERROR] Check if PostgreSQL started correctly (see postgres/logfile)', flush=True)
            sys.exit(1)
        print('[OK] PostgreSQL is ready', flush=True)

    # CRITICAL: Generate Prisma client BEFORE starting LiteLLM
    print('[INFO] Preparing Prisma database client...', flush=True)
    if not generate_prisma_client():
        print('[ERROR] Failed to generate Prisma client', flush=True)
        print('[ERROR] LiteLLM cannot start without it', flush=True)
        sys.exit(1)

    print('[INFO] Starting LiteLLM...', flush=True)

    # Start LiteLLM with proper logging
    # CRITICAL: Don't capture output - let it stream to console so we see errors
    try:
        # Create log file for debugging
        log_file = 'litellm_startup.log'
        with open(log_file, 'w') as logf:
            logf.write(f'Starting LiteLLM on port {litellm_port}\n')
            logf.write(f'Database URL: {database_url}\n')
            logf.write('---\n')
        
        # Start LiteLLM process
        # CRITICAL: Merge loaded env_vars with system environment
        process_env = os.environ.copy()
        process_env.update(env_vars)
        process_env['PYTHONIOENCODING'] = 'utf-8'
        process_env['PYTHONUTF8'] = '1'  # Fix Windows charmap encoding warnings
        process_env['LITELLM_DISABLE_COST_TRACKING'] = 'true'  # Disable enterprise cost checking
        
        process = subprocess.Popen(
            [
                'litellm',
                '--config', 'config.yaml',
                '--port', str(litellm_port),
                '--host', '127.0.0.1'
            ],
            env=process_env,  # ← Merged environment
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        print('[INFO] LiteLLM process started, waiting for startup...', flush=True)

        # Stream LiteLLM output to console and log file while checking readiness
        startup_complete = False
        read_timeout = time.time() + 60  # 60 second startup timeout
        
        while True:
            # Check if process died
            poll_result = process.poll()
            if poll_result is not None:
                # Process exited
                print(f'[ERROR] LiteLLM process exited with code {poll_result}', flush=True)
                print('[ERROR] Remaining output:', flush=True)
                remaining = process.stdout.read()
                if remaining:
                    print(remaining, flush=True)
                    with open(log_file, 'a') as logf:
                        logf.write(remaining)
                sys.exit(poll_result if poll_result != 0 else 1)
            
            # Check if startup timeout exceeded
            if time.time() > read_timeout:
                print('[ERROR] LiteLLM startup timeout (60 seconds)', flush=True)
                process.terminate()
                sys.exit(1)
            
            # Read available output
            try:
                line = process.stdout.readline()
                if line:
                    print(line.rstrip(), flush=True)
                    with open(log_file, 'a') as logf:
                        logf.write(line)
                    
                    # Check for successful startup indicators
                    if 'Application startup complete' in line or 'Uvicorn running' in line:
                        startup_complete = True
                        break
                else:
                    # Small delay to avoid busy loop
                    time.sleep(0.1)
            except Exception as e:
                print(f'[WARN] Error reading output: {e}', flush=True)
                time.sleep(0.1)

        # Verify LiteLLM is actually listening
        print('[INFO] Waiting for LiteLLM to accept connections...', flush=True)
        if not is_litellm_ready(port=litellm_port, timeout=30):
            print(f'[ERROR] LiteLLM is not accepting connections on port {litellm_port}', flush=True)
            print(f'[ERROR] Check {log_file} for startup details', flush=True)
            process.terminate()
            sys.exit(1)

        print('[OK] LiteLLM is ready', flush=True)
        print('[OK] Uvicorn running', flush=True)  # Signal for Pinokio
        
        # Keep the process running
        process.wait()

    except KeyboardInterrupt:
        print('[INFO] LiteLLM stopped', flush=True)
    except FileNotFoundError:
        print('[ERROR] LiteLLM command not found. Is it installed?', flush=True)
        print('[ERROR] Try: pip install litellm[proxy]', flush=True)
        sys.exit(1)
    except Exception as e:
        print(f'[ERROR] LiteLLM failed: {e}', flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
