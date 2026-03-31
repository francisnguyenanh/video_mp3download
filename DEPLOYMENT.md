# Production Deployment Guide

## ⚠️ Before Going Live

This guide helps you deploy the Video Downloader securely to production.

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` in `app.py` to a secure random string
- [ ] Set `debug=False` in `app.py`
- [ ] Add authentication for user accounts (basic Flask-Login)
- [ ] Use HTTPS/SSL certificate
- [ ] Set up firewall rules
- [ ] Configure CORS properly (not `*`)
- [ ] Add rate limiting to prevent abuse
- [ ] Monitor disk space automatically
- [ ] Set file size limits
- [ ] Add virus scanning for downloaded files

## 🚀 Deployment Options

### Option 1: Heroku (Cloud Platform)

```bash
# Install Heroku CLI
brew install heroku/brew/heroku

# Login
heroku login

# Create Procfile
echo "web: python app.py" > Procfile

# Create requirements.txt (already done)

# Deploy
heroku create <app-name>
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

### Option 2: Docker Container

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py downloader.py ./
COPY templates/ templates/
COPY static/ static/

# Create downloads directory
RUN mkdir -p downloads

# Expose port
EXPOSE 5000

# Run app
CMD ["python", "app.py"]
```

**Build and run:**
```bash
docker build -t video-downloader .
docker run -p 5000:5000 -v downloads:/app/downloads video-downloader
```

### Option 3: AWS EC2

```bash
# SSH into EC2 instance
ssh -i key.pem ec2-user@your-instance

# Update system
sudo yum update -y

# Install Python and ffmpeg
sudo yum install python3 ffmpeg -y

# Clone/upload project
git clone <repo-url> video-downloader
cd video-downloader

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with Gunicorn (production WSGI)
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### Option 4: Ubuntu/VPS Server

```bash
# Update
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3 python3-pip ffmpeg -y

# Clone project
git clone <repo-url> video-downloader
cd video-downloader

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install and configure Nginx (reverse proxy)
sudo apt install nginx -y

# Create Nginx config file: /etc/nginx/sites-available/default
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔧 Production Configuration

### 1. Secure Secret Key

```python
# app.py
import secrets
SECRET_KEY = secrets.token_hex(32)  # Generate: 64 character hex string
```

### 2. Environment Variables

Create `.env`:
```
SECRET_KEY=your-secure-key
DEBUG=False
OUTPUT_DIR=/var/www/downloads
MAX_FILE_SIZE=5000000000
DATABASE_URL=...
```

Load in `app.py`:
```python
from os import environ
from dotenv import load_dotenv

load_dotenv()

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
DEBUG = environ.get('DEBUG', 'False') == 'True'
```

### 3. Add Authentication

```python
# In app.py
from flask_login import LoginManager, login_required

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.route('/api/add', methods=['POST'])
@login_required
def add_to_queue():
    # Protected endpoint
    ...
```

### 4. Rate Limiting

```python
# app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/add', methods=['POST'])
@limiter.limit("10 per hour")
def add_to_queue():
    ...
```

### 5. File Size Limits

```python
# app.py
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max

MAX_DOWNLOAD_SIZE = 4 * 1024 * 1024 * 1024  # 4GB per file
```

### 6. Auto-cleanup Old Files

```python
# Add to app.py
import time
from pathlib import Path

def cleanup_old_files(days=30):
    """Remove files older than X days"""
    cutoff_time = time.time() - (days * 86400)
    
    for file in Path(OUTPUT_DIR).glob('*'):
        if file.stat().st_mtime < cutoff_time:
            file.unlink()

# Run scheduled cleanup
from schedule import every, run_pending
import threading

def scheduled_cleanup():
    every().day.at("02:00").do(cleanup_old_files)
    while True:
        run_pending()
        time.sleep(60)

cleanup_thread = threading.Thread(target=scheduled_cleanup, daemon=True)
cleanup_thread.start()
```

## 📊 Monitoring & Logging

### Application Logging

```python
# In app.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=10)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
```

### Disk Space Monitoring

```python
import shutil

def check_disk_space():
    disk = shutil.disk_usage(OUTPUT_DIR)
    free_gb = disk.free / (1024**3)
    
    if free_gb < 1:  # Less than 1GB
        logger.warning(f"Low disk space: {free_gb:.2f}GB free")
        # Trigger cleanup
```

## 🔒 SSL/HTTPS Setup

### Using Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### In Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 📈 Performance Optimization

### 1. Caching

```python
# app.py
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/files')
@cache.cached(timeout=60)  # Cache for 60 seconds
def list_files():
    ...
```

### 2. Compression

```python
# app.py
from flask_compress import Compress

Compress(app)
```

### 3. Load Balancing

Use Nginx to distribute across multiple Flask instances:

```nginx
upstream flask_app {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}

server {
    location / {
        proxy_pass http://flask_app;
    }
}
```

## 🚨 Backup & Disaster Recovery

### Automated Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup downloads
tar -czf $BACKUP_DIR/downloads_$DATE.tar.gz /path/to/downloads/

# Backup database (if any)
mysqldump -u user -p database > $BACKUP_DIR/db_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -mtime +30 -delete
```

Schedule in crontab:
```bash
0 2 * * * /path/to/backup.sh
```

## ✅ Pre-Launch Checklist

- [ ] All secrets in environment variables
- [ ] Debug mode OFF
- [ ] HTTPS/SSL configured
- [ ] Firewall rules set
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Backups automated
- [ ] Monitoring set up
- [ ] Database credentials secure
- [ ] Email notifications configured
- [ ] DNS configured
- [ ] Health check endpoint added
- [ ] Error tracking enabled (Sentry, etc.)
- [ ] Performance tested
- [ ] Load tested
- [ ] Security audit passed

## 📞 Monitoring Services

Consider these services for production monitoring:

- **Sentry** - Error tracking
- **New Relic** - Performance monitoring
- **DataDog** - Infrastructure monitoring
- **Azure Monitor** - Azure-based monitoring
- **CloudFlare** - CDN & DDoS protection

## 🆘 Troubleshooting Production

### Issue: High Memory Usage
- Check for memory leaks in download threads
- Implement job queue limits
- Monitor with: `top`, `ps aux | grep app.py`

### Issue: Socket.IO Not Working
- Ensure eventlet is installed
- Check firewall for WebSocket (port 5000)
- Verify nginx config allows WebSocket upgrades

### Issue: Slow Downloads
- Check server bandwidth
- Monitor CPU usage
- Verify ffmpeg installation
- Check source server speed

---

**Ready for production? Follow this guide carefully! 🚀**
