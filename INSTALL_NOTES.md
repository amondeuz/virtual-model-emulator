# Installation & Setup Notes

## What Gets Installed

### Python Dependencies
- litellm (routing engine)
- prisma (database ORM)
- psycopg2 (PostgreSQL client)
- uvicorn (ASGI server)

### PostgreSQL Binary
- Platform-specific PostgreSQL 16 binaries
- Downloaded from EnterpriseDB
- SHA-256 verification
- ~300 MB download

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

### PostgreSQL binary download failed
- Check internet connection
- Verify SHA-256 of downloaded file
- Try reinstalling

### Port already in use
- Check running processes: `lsof -i :5450`
- LiteLLM uses 11435
- API Server uses 8775

### Cannot create database
- Check PostgreSQL is running
- Check password in .env
- Check createdb binary exists

### Prisma client not found
- Run: `pip install prisma`
- Restart app

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
