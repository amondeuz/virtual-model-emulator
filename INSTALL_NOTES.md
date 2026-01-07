# Installation & Setup Notes (v2.2.2)

## What Gets Installed

### Python Dependencies
- litellm>=1.10.0 (Direct SDK usage)
- cryptography>=41.0.0 (API key encryption)
- PyYAML>=6.0 (Configuration management)
- pytest>=7.0.0 (Unit testing - optional for development)

### Configuration Files
- .env (database and service config)
- config.yaml (LiteLLM routing)
- public/ (web UI files)

### Data Directory
- postgres/ (binaries and data)

## Platform-Specific Notes

### Windows 10+ (Fully Supported)
- Everything works automatically
- Uses .exe binaries
- Process isolation works correctly

### macOS (Fully Supported)
- Run: `python app_launcher.py`

### Linux (Fully Supported)
- Run: `python app_launcher.py`

## First Time Checklist

After installation:
- [ ] App shows "Running" in Pinokio
- [ ] All services started (check console)
- [ ] Can access http://localhost:8775/config.html
- [ ] UI loads with both tabs
- [ ] No error messages in console

## Verification

```bash
# API Server
curl http://127.0.0.1:8775/health
```

## Troubleshooting

### "Port 8775 already in use"
- Check: `lsof -i :8775` (macOS/Linux) or `netstat -ano | findstr :8775` (Windows)
- Kill the process or change API_SERVER_PORT in .env

### "Failed to load models"
- Check internet connection: `curl -I https://api.groq.com`
- Verify API key is valid in connect.html tab
- Check error logs: `tail -f config/errors.log`

### "No models loading after adding API key"
- Click "Refresh" button to fetch models from provider
- Check audit log: `cat config/audit.log | grep MODELS`
- Some providers have rate limits - wait 60 seconds and retry

### "Keys showing in error messages"
- This should never happen - report as security bug
- Check error messages are sanitized: `grep -v "sk-" config/errors.log`

## Performance Tips

1. Close other applications (saves RAM)
2. Disable browser extensions
3. Use modern browser (better JS)

## Uninstall

From Pinokio: Right-click app → Uninstall

Complete removal: `rm -rf ~/.pinokio/api/virtual-model-emulator`

## Getting Help

1. Check Pinokio console for errors
2. Verify internet connection
3. Check disk space (needs 2GB)
4. Try deleting .env and reinstalling
