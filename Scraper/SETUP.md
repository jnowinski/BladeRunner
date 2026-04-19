# Quick Setup Guide

Follow these steps to get the scraper running:

## 1. Install Python Dependencies

```powershell
cd C:\Career\CSE881\BladeRunner\Scraper
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```


## 3. Configure Credentials

```powershell
# Copy example env file
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

Required credentials:
- **Twitter**: Bearer Token from developer.twitter.com
- **Reddit**: Client ID and Secret from reddit.com/prefs/apps
- **Bluesky**: Handle and App Password from bsky.app/settings/app-passwords

## 4. Test Configuration

```powershell
python test_setup.py
```

This will verify:
- Dependencies installed correctly
- Database connection works
- API credentials are valid

## 5. Start Scraping!

```powershell
# Start all platforms
python scraper.py start

# Or start specific platforms
python scraper.py start --platforms twitter reddit bluesky
```

## 6. Monitor

```powershell
# Check status
python scraper.py status

# View logs
type logs\scraper.log
# Or tail in PowerShell
Get-Content logs\scraper.log -Wait -Tail 20
```

## 7. Stop When Done

```powershell
python scraper.py stop
```

## Quick Troubleshooting

### "Module not found" errors
```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### "Database connection failed"
- Ensure `data/` directory is writable
- Check disk space available
- If corrupted: delete `data/scraper.db` and restart

### "Authentication failed" for a platform
- Double-check API credentials in `.env`
- Verify credentials are not expired
- Check platform-specific requirements (e.g., app passwords for Bluesky)

### Daemon won't start
```powershell
# Remove stale PID file
del scraper.pid
python scraper.py start
```

1. Customize search queries in `config.py`
2. Adjust poll intervals for each platform

---

For detailed information, see [README.md](README.md)
