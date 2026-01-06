# Installation & Setup Notes (v2.2.1)

## What Gets Installed

### Python Dependencies (Simplified for v2.2.1)
- litellm>=1.10.0 (Direct SDK usage - no proxy needed)
- cryptography>=41.0.0 (API key encryption)
- PyYAML>=6.0 (Configuration management)
- pytest>=7.0.0 (Unit testing)

### What You DON'T Need Anymore (v2.2.0+)
- PostgreSQL binary (removed - no database needed)
- LiteLLM proxy server (using SDK directly)
- Prisma (no database)
- psycopg2 (no PostgreSQL)
- uvicorn (not needed)

### Configuration Files
- .env (database and service config)
- config.yaml (LiteLLM routing)
- public/ (web UI files)

### Data Directory
- postgres/ (binaries and data)

## Platform-Specific Notes

### Windows 11 (Fully Supported)
- Everything works automatically
- Uses .exe binaries
- Process isolation works correctly

### macOS (Partial Support)
- Manual PostgreSQL setup: `brew install postgresql`
- Set PATH: `export PATH="/usr/local/opt/postgresql/bin:$PATH"`
- Run: `python app_launcher.py`

### Linux (Partial Support)
- Use system PostgreSQL: `sudo apt install postgresql`
- Start service: `sudo systemctl start postgresql`
- Set in .env: `DATABASE_URL=postgresql://postgres:password@localhost:5432/litellm`
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
# PostgreSQL
pg_isready -h 127.0.0.1 -p 5450

# LiteLLM
curl http://127.0.0.1:11435/health

# API Server
curl http://127.0.0.1:8775/
```

## Troubleshooting

### "Port 8775 already in use"
- Check: `lsof -i :8775` (macOS/Linux) or `netstat -ano | findstr :8775` (Windows)
- Kill the process or change API_SERVER_PORT in .env
- API Server uses port 8775 only (no PostgreSQL or LiteLLM proxy)

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
3. Run on SSD (better PostgreSQL performance)
4. Use modern browser (better JS)

## Uninstall

From Pinokio: Right-click app → Uninstall

Complete removal: `rm -rf ~/.pinokio/api/virtual-model-emulator`

## Getting Help

1. Check Pinokio console for errors
2. Check PostgreSQL logfile: postgres/logfile
3. Verify internet connection
4. Check disk space (needs 2GB)
5. Try deleting .env and reinstalling
