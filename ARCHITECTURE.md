# Virtual Model Emulator - Architecture

## Service Architecture

Virtual Model Emulator v2.2.2 uses a simplified single-service architecture.

### Master Process: app_launcher.py
- Starts API Server as subprocess
- Monitors service continuously
- Handles graceful shutdown on signal
- Pinokio monitors this single process

### Service: API Server (Port 8775)
- Serves web UI (config.html, connect.html)
- Manages provider configuration
- Handles OpenAI-compatible chat completions
- Uses LiteLLM SDK directly (no proxy needed)
- Direct communication with provider APIs

## Simplified Data Flow

```
Browser (config.html/connect.html)
    ↓
API Server (8775) using LiteLLM SDK
    ↓
Provider APIs (OpenAI, Anthropic, Groq, etc.)
```

## Key Design Decisions

### Single Service Architecture
- Simplified from v2.1.4 (which had PostgreSQL + LiteLLM proxy)
- All functionality in one Python HTTP server
- No external database needed
- LiteLLM SDK integrated directly
- Faster startup, easier deployment

### Local-First Design
- Listens only on localhost (127.0.0.1)
- No internet exposure
- All state persisted to local JSON files
- Master encryption key from environment variable

### Direct SDK Integration
- Uses LiteLLM Python SDK directly
- No separate proxy server
- Reduced complexity, fewer dependencies
- Single configuration point

## Cross-Tab Synchronization

When user adds an account in connect.html:

1. User adds account in connect.html
2. POST /providers/connect saves to accounts.json
3. connect.html broadcasts via BroadcastChannel
4. config.html receives message
5. config.html calls /config/state
6. Account list updates automatically

Fallback: If BroadcastChannel unavailable, polling every 30 seconds detects changes.

## Configuration Storage

- **accounts.json**: Saved accounts with encrypted API keys
- **emulations.json**: Active model emulations with encrypted API keys
- **config.yaml**: Master encryption key (legacy support)
- **Environment**: VME_MASTER_KEY for encrypted storage

All sensitive files set to 0600 permissions.

## Performance

- Startup: ~5 seconds
- Model switching: <2 seconds
- Memory: ~100-150 MB (no database)
- Concurrent requests: 4-6 (depends on model)
- Rate limiting: 10 requests/second per IP

## Migration from v2.1.4

If upgrading from v2.1.4:
- PostgreSQL no longer used - can delete postgres/ directory
- LiteLLM proxy no longer needed - removed from v2.2.0+
- Configuration moved to JSON files
- API endpoint: still port 8775
- API key format: now encrypted with master key
