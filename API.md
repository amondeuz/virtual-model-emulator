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
