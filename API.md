# Virtual Model Emulator - API Documentation

## Base URL

```
http://localhost:8775
```

## Endpoints

### GET /config/state

Get full application state.

**Response:**
```json
{
  "accounts": [{"provider": "groq", "accountName": "Personal"}],
  "providers": [{"id": "groq", "name": "Groq", "hasApiKey": true}],
  "emulatorActive": true,
  "providerOnline": true
}
```

### GET /models?provider=X&force=false

List available models for provider. Cached for 1 hour.

**Parameters:** `provider` (required), `force` (optional, bypass cache)

**Response:**
```json
{
  "models": [
    {"id": "llama-3.3-70b-versatile", "label": "llama-3.3-70b-versatile", "provider": "groq"}
  ],
  "cached": false
}
```

### GET /health

Health check.

**Response:**
```json
{"online": true, "message": "API server running"}
```

### GET /emulator/status

Get current emulator status and configuration.

**Response:**
```json
{
  "emulatorRunning": true,
  "providerOnline": true,
  "currentConfig": {
    "emulatedModelName": "gpt-4",
    "providerName": "Groq"
  }
}
```

### GET /emulator/active

Get all active emulations (without API keys).

**Response:**
```json
{
  "active": [
    {
      "id": "uuid-123",
      "emulatedName": "gpt-4",
      "actualModel": "groq/llama-3.3-70b",
      "provider": "groq"
    }
  ],
  "count": 1
}
```

### GET /providers/list

Get list of all supported providers.

**Response:**
```json
{
  "providers": [
    {"id": "groq", "name": "Groq", "envVar": "GROQ_API_KEY"},
    {"id": "openai", "name": "OpenAI", "envVar": "OPENAI_API_KEY"}
  ]
}
```

### GET /providers/accounts

Get list of saved provider accounts (names only).

**Response:**
```json
[
  {"provider": "groq", "accountName": "Personal"},
  {"provider": "openai", "accountName": "Work"}
]
```

### POST /providers/connect

Add provider account.

**Request:**
```json
{"provider": "groq", "accountName": "Personal", "apiKey": "gsk_..."}
```

**Response:** `{"success": true}`

### POST /providers/disconnect

Remove provider account.

**Request:**
```json
{"provider": "groq", "accountName": "Personal"}
```

### POST /emulator/start

Enable model emulation.

**Request:**
```json
{
  "provider": "groq",
  "account": "Personal",
  "model": "llama-3.3-70b-versatile",
  "emulatedModelName": "gpt-4"
}
```

**Response:**
```json
{
  "success": true,
  "emulatedName": "gpt-4",
  "actualModel": "groq/llama-3.3-70b-versatile"
}
```

### POST /emulator/stop

Disable all emulations.

**Response:** `{"success": true, "deleted": 1}`

### POST /v1/chat/completions

OpenAI-compatible chat endpoint.

**Request:**
```json
{
  "model": "gpt-4",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 100
}
```

**Response**: OpenAI-compatible format.

## Rate Limiting

- **Limit**: 10 requests/second per IP
- **Response on limit**: 429 Too Many Requests

## CORS (Cross-Origin Resource Sharing)

The API supports CORS for browser-based clients like Open WebUI.

### Default Behavior
- **Localhost Wildcard**: Any `http://localhost:*` or `http://127.0.0.1:*` origin is automatically allowed
- **Pre-configured Ports**: 3000, 8080, 8775, 42004 explicitly allowed
- **Credentials**: `Access-Control-Allow-Credentials: true` for cookie support
- **Preflight Cache**: OPTIONS responses cached 24 hours

### Allowed Methods
`GET`, `POST`, `OPTIONS`

### Allowed Headers
`Content-Type`, `Authorization`, `X-Requested-With`

### Adding Production Origins
Add to `config.yaml`:
```yaml
general_settings:
  allowed_origins:
    - "https://your-domain.com"
```

### Security Logging
Blocked CORS origins are logged:
```
[SECURITY] CORS blocked origin: https://untrusted-site.com
```

## Configuration

### Environment Variables
- `API_SERVER_PORT`: Port for API server (default: 8775)
- `VME_MASTER_KEY`: Master encryption key (optional - generated if not set)
- `ADMIN_SECRET`: Bearer token for admin endpoints (optional)
- `SSL_CERT_FILE`: Path to SSL certificate (optional - enables HTTPS)
- `SSL_KEY_FILE`: Path to SSL private key (optional - enables HTTPS)

## Caching

Model lists cached for 1 hour. Bypass with `?force=true`.

## Logs

- **Audit**: `config/audit.log` (all actions)
- **Errors**: `config/errors.log` (failures only)

## Admin Endpoints

### POST /admin/rotate-key

Rotate master encryption key (requires ADMIN_SECRET env var).

**Request:** `{"secret": "your-secret"}`

**Response:** `{"success": true, "message": "Master key rotated"}`

### GET /admin/cache-stats

Get caching statistics.

**Response:** `{"cache": {"cached_providers": 2}, "ttl_seconds": 3600}`
