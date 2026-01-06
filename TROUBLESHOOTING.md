# Troubleshooting Guide

## "No API key found for provider"

**Solution**: Go to "Manage API Keys" tab, add your provider account.

## "Models aren't loading"

**Causes**: Internet down, provider offline, invalid API key, rate limited.

**Fixes**:
```bash
# Test connection
curl http://localhost:8775/health

# Check logs
tail config/errors.log

# Force refresh models
curl "http://localhost:8775/models?provider=groq&force=true"
```

## "Emulator won't start"

**Checks**:
1. All dropdowns selected (Account, Provider, Model)
2. Emulated name filled in (or empty for transparent mode)
3. Provider is online: `curl http://localhost:8775/health`

**Restart**:
```bash
# In Pinokio: Stop → Wait 5s → Start
```

## "Getting 429 Rate Limited"

**Cause**: Making >10 requests/second.

**Fix**: Space out requests with delays.

## "Port 8775 already in use"

**Find process**:
```bash
# Windows
netstat -ano | findstr :8775

# Mac/Linux
lsof -i :8775
```

**Kill process** or change port in `.env`.

## "Master key lost/corrupted"

**Warning**: This deletes all saved API keys.
```bash
# Delete and restart
rm config/config.yaml
# Restart Pinokio
# Re-add all API keys
```

## "Can't connect from another computer"

**By design**: Emulator only listens on localhost (127.0.0.1).

To access remotely:
```bash
# Via SSH tunnel
ssh -L 8775:localhost:8775 user@remote-ip
curl http://localhost:8775/config/state
```

## Debug Checklist

1. `curl http://localhost:8775/health` - Server running?
2. `curl http://localhost:8775/config/state` - Full state?
3. `tail config/errors.log` - Any errors?
4. Check Pinokio console output
5. Restart Pinokio

---
