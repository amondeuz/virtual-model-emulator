"""Unified launcher for Virtual Model Emulator.

This is the single entry point that Pinokio monitors. It starts all services
and keeps them alive until shutdown.
"""
import os
import signal
import subprocess
import sys
import threading
import time

from env_loader import load_env

# Global shutdown flag
shutdown_requested = False
stop_event = threading.Event()

# Track child processes
processes = {}


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print(f'\n[INFO] Received signal {sig}, initiating shutdown...', flush=True)
    shutdown_requested = True
    stop_event.set()


def get_creation_flags():
    """Get subprocess creation flags for Windows process isolation."""
    if sys.platform == 'win32':
        return subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    return 0


def get_process_env():
    """Get environment variables for subprocesses."""
    env = os.environ.copy()
    env.update({
        'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONLEGACYWINDOWSSTDIO': '1'
    })
    return env


def stream_output(process, name, ready_event=None, ready_pattern=None):
    """Stream subprocess output to console using non-blocking reads.

    CRITICAL: Uses read() instead of readline() to avoid Windows deadlock.
    Windows pipe buffers are only 4KB. If subprocess writes faster than parent
    reads, and we're waiting for a newline that doesn't come, the pipe fills
    and both processes deadlock.

    Args:
        process: The subprocess to stream from
        name: Name for logging prefix
        ready_event: Optional threading.Event to set when ready_pattern is found
        ready_pattern: Pattern that indicates service is ready
    """
    buffer = ""

    try:
        while not stop_event.is_set():
            # Check if process has exited
            if process.poll() is not None:
                # Process died, read any remaining buffered output
                try:
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.splitlines():
                            if line.strip():
                                print(f'[{name}] {line}', flush=True)
                                if ready_event and ready_pattern and ready_pattern in line:
                                    ready_event.set()
                except Exception:
                    pass
                break

            # Read available data in chunks (non-blocking style)
            try:
                # Read a chunk of data - this is safer than readline()
                chunk = process.stdout.read(4096)
                if chunk:
                    buffer += chunk
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            print(f'[{name}] {line.rstrip()}', flush=True)
                            if ready_event and ready_pattern and ready_pattern in line:
                                ready_event.set()
                else:
                    # No data available, small sleep to avoid busy loop
                    time.sleep(0.05)
            except (BlockingIOError, ValueError):
                # Pipe closed or other issue
                time.sleep(0.05)

    except Exception as e:
        print(f'[ERROR] {name} stream error: {e}', flush=True)
    finally:
        # Print any remaining buffered content
        if buffer.strip():
            print(f'[{name}] {buffer.rstrip()}', flush=True)


def start_service(name, command, ready_pattern=None, timeout=60):
    """Start a service and wait for it to be ready.

    Args:
        name: Service name for logging
        command: Command to run (list of strings)
        ready_pattern: Pattern in output that indicates service is ready
        timeout: Maximum seconds to wait for ready pattern

    Returns:
        subprocess.Popen: The process object, or None on failure
    """
    print(f'[INFO] Starting {name}...', flush=True)

    try:
        process = subprocess.Popen(
            command,
            env=get_process_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=get_creation_flags()
        )

        processes[name] = process

        if ready_pattern:
            ready_event = threading.Event()

            # Start output streaming thread
            stream_thread = threading.Thread(
                target=stream_output,
                args=(process, name, ready_event, ready_pattern),
                daemon=True
            )
            stream_thread.start()

            # Wait for ready signal
            if not ready_event.wait(timeout=timeout):
                # Check if process died
                if process.poll() is not None:
                    print(f'[ERROR] {name} exited with code {process.poll()}', flush=True)
                    return None
                print(f'[WARN] {name} did not signal ready within {timeout}s, continuing...', flush=True)
        else:
            # Start output streaming thread without ready check
            stream_thread = threading.Thread(
                target=stream_output,
                args=(process, name),
                daemon=True
            )
            stream_thread.start()

        print(f'[OK] {name} started (PID: {process.pid})', flush=True)
        return process

    except Exception as e:
        print(f'[ERROR] Failed to start {name}: {e}', flush=True)
        return None


def cleanup_processes():
    """Terminate all child processes gracefully."""
    print('[INFO] Cleaning up processes...', flush=True)

    for name, process in processes.items():
        if process and process.poll() is None:
            print(f'[INFO] Stopping {name}...', flush=True)
            try:
                process.terminate()
                try:
                    process.wait(timeout=10)
                    print(f'[OK] {name} stopped', flush=True)
                except subprocess.TimeoutExpired:
                    print(f'[WARN] {name} not responding, forcing...', flush=True)
                    process.kill()
                    process.wait()
                    print(f'[OK] {name} killed', flush=True)
            except Exception as e:
                print(f'[ERROR] Failed to stop {name}: {e}', flush=True)

    processes.clear()


def monitor_processes():
    """Monitor running processes and report any failures."""
    while not stop_event.is_set():
        for name, process in list(processes.items()):
            if process and process.poll() is not None:
                exit_code = process.poll()
                print(f'[ERROR] {name} exited unexpectedly with code {exit_code}', flush=True)

                # Critical service failure - trigger shutdown
                if name in ['PostgreSQL', 'LiteLLM']:
                    print(f'[ERROR] Critical service {name} failed, shutting down...', flush=True)
                    stop_event.set()
                    return

        # Check every second
        time.sleep(1)


def main():
    """Main entry point - starts all services and monitors them."""
    global shutdown_requested

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print('[INFO] Virtual Model Emulator starting...', flush=True)

    # Load environment
    print('[INFO] Loading environment...', flush=True)
    try:
        env_vars = load_env()
        # Update current process environment
        os.environ.update(env_vars)
        print('[OK] Environment loaded', flush=True)
    except SystemExit:
        print('[ERROR] Failed to load environment', flush=True)
        sys.exit(1)

    # Validate configuration
    print('[INFO] Validating configuration...', flush=True)
    validate_proc = start_service(
        'Validate',
        [sys.executable, 'validate_config.py'],
        ready_pattern='Environment validated',
        timeout=30
    )

    if validate_proc is None:
        print('[ERROR] Configuration validation failed', flush=True)
        cleanup_processes()
        sys.exit(1)

    # Wait for validation to complete
    validate_proc.wait()
    if validate_proc.returncode != 0:
        print('[ERROR] Configuration validation failed', flush=True)
        cleanup_processes()
        sys.exit(1)

    del processes['Validate']  # Remove from tracking
    print('[OK] Configuration validated', flush=True)

    # Start PostgreSQL
    postgres_proc = start_service(
        'PostgreSQL',
        [sys.executable, 'start_postgres.py'],
        ready_pattern='PostgreSQL ready',
        timeout=60
    )

    if postgres_proc is None:
        print('[ERROR] Failed to start PostgreSQL', flush=True)
        cleanup_processes()
        sys.exit(1)

    # Give PostgreSQL a moment to fully initialize
    time.sleep(1)

    # Start LiteLLM
    litellm_proc = start_service(
        'LiteLLM',
        [sys.executable, 'start_litellm.py'],
        ready_pattern='Uvicorn running',
        timeout=120
    )

    if litellm_proc is None:
        print('[ERROR] Failed to start LiteLLM', flush=True)
        cleanup_processes()
        sys.exit(1)

    # Give LiteLLM a moment to fully initialize
    time.sleep(1)

    # Start API Server
    server_proc = start_service(
        'APIServer',
        [sys.executable, 'server.py'],
        ready_pattern='http://localhost:',
        timeout=30
    )

    if server_proc is None:
        print('[ERROR] Failed to start API Server', flush=True)
        cleanup_processes()
        sys.exit(1)

    # All services started successfully
    print('', flush=True)
    print('=' * 50, flush=True)
    print('All services started successfully', flush=True)
    print('=' * 50, flush=True)
    print('', flush=True)
    print('[INFO] Entering monitoring mode - press Ctrl+C to stop', flush=True)

    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_processes, daemon=True)
    monitor_thread.start()

    # Main loop - keep running until shutdown
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\n[INFO] Keyboard interrupt received', flush=True)
    finally:
        print('[INFO] Shutting down...', flush=True)
        cleanup_processes()
        print('[INFO] Shutdown complete', flush=True)


if __name__ == '__main__':
    main()
