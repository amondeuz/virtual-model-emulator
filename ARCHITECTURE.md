# Virtual Model Emulator - Architecture

## Service Architecture

Virtual Model Emulator v2.1.4 runs three coordinated services under a single master process.

### Master Process: app_launcher.py
- Starts all services as subprocesses
- Monitors each service continuously
- Handles graceful shutdown on signal
- Pinokio monitors this single process

### Service 1: PostgreSQL (Port 5450-5550)
- Stores provider accounts and API keys
- Stores model configurations
- Automatically finds open port if 5450 is busy
- Started by: start_postgres.py
- Managed by: postgres_manager.py

### Service 2: LiteLLM Proxy (Port 11435)
- Routes API calls to configured providers
- Translates responses back to OpenAI format
- Reads config from PostgreSQL
- Started by: start_litellm.py
- Configuration: config.yaml

### Service 3: API Server (Port 8775)
- Serves web UI (config.html, connect.html)
- Manages provider configuration
- Communicates with PostgreSQL and LiteLLM
- Started by: server.py
- Language: Python http.server

## Data Flow

```
Browser (config.html/connect.html)
    ↓
API Server (8775)
    ↓
PostgreSQL (5450-5550)
    ↓
LiteLLM Proxy (11435)
    ↓
AI Provider APIs
```

## Cross-Tab Synchronization

When user adds an account in connect.html tab:

1. User adds account in connect.html
2. POST /providers/connect saves to PostgreSQL
3. connect.html broadcasts via BroadcastChannel
4. config.html receives message
5. config.html calls fetchState(true)
6. Account list updates automatically

Fallback: If BroadcastChannel unavailable, polling every 10 seconds detects changes.

## Port Allocation

PostgreSQL uses ports 5450-5550:
- Starts on 5450
- If busy, tries 5451, 5452, etc.
- Updates DATABASE_URL with actual port
- All services coordinate via environment variables

## Key Design Decisions

### Single Master Process
- Pinokio expects one monitored process
- All services run as subprocesses
- If master exits, app is stopped

### Background Threading
- Windows has 4KB pipe buffers
- Threading prevents deadlock
- Each service has dedicated output thread
- Main thread never blocks on I/O

### Cross-Tab Communication
- BroadcastChannel for modern browsers
- Polling fallback for older browsers
- Visibility change detection for immediate updates
- 10-second polling as final fallback

### Dynamic Port Allocation
- Avoids conflicts with existing services
- Automatically finds open port
- Updates configuration at runtime
- All services coordinate via environment

## Error Handling

### Service Failures
- PostgreSQL: Exits if cannot start
- LiteLLM: Logs exit code, continues monitoring
- API Server: Port error exits, LiteLLM offline is warning only

### Graceful Shutdown
- Catches SIGINT and SIGTERM
- Terminates services in reverse order
- Waits 10 seconds, then kills if needed
- Cleans up resources

## Performance

- Startup: 10-20 seconds
- Model switching: <2 seconds
- Memory: 300-500 MB baseline
- Concurrent requests: 4-6 (depends on model)

See INSTALL_NOTES.md for optimization tips.
