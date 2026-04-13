# GlanceWatch: A Lightweight Bridge Between Glances and Uptime Kuma

## How I Built a Zero-Configuration System Monitor That Just Works

---

**TL;DR:** I created GlanceWatch, a lightweight Python tool that bridges Glances system metrics with Uptime Kuma monitoring. One command to install, automatic background service, and dead-simple HTTP health checks. Available on PyPI at https://pypi.org/project/glancewatch/

---

## What's New in v1.2.6 🚀

### Bug Fixes
- **Glances API v4 Compatibility** — Now works seamlessly with Glances 4.x (tries API v4 first, falls back to v3)
- **Fixed async response handling** — Resolved "object dict can't be used in 'await' expression" error

### v1.2.5 Features
- **System Info Panel** — View hostname, OS, Python version, and uptime at a glance
- **Sparkline Mini-Charts** — Visual trend indicators for CPU, RAM, and Disk metrics
- **Export Button** — Download monitoring data as JSON for analysis
- **Updated Dependencies** — FastAPI 0.115+, Pydantic 2.10+, httpx 0.27+

---

## The Problem: Monitoring Should Be Simple

If you're running servers (production, homelab, or just a Raspberry Pi), you know the drill:

1. Install monitoring tools
2. Configure them (lots of YAML)
3. Set up alerting
4. Hope it works when SSH disconnects
5. Debug why it stopped running

I was using Glances (fantastic system monitor) and Uptime Kuma (beautiful uptime dashboard), but they didn't talk to each other. I needed a bridge that would:

- Return HTTP 200 when system is healthy
- Return HTTP 503 when CPU/RAM/Disk exceeds thresholds
- Run in the background without babysitting
- Install with a single command
- **Just. Freaking. Work.**

So I built GlanceWatch.

---

## The Design Philosophy: Zero Configuration

I hate configuration files. I hate services that die when you close your terminal. I hate tools that require 10 steps to get started.

**GlanceWatch's Philosophy:**

\`\`\`bash
pip install glancewatch
# Done. It's running. Forever.
\`\`\`

No Docker. No docker-compose.yml. No systemd unit files to debug. Just Python.

---

## The Architecture: Stupid Simple

\`\`\`
┌─────────────┐
│   Glances   │  ← System metrics (CPU, RAM, Disk)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ GlanceWatch │  ← Threshold checks + HTTP endpoints
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Uptime Kuma │  ← Monitors HTTP status codes
└─────────────┘
\`\`\`

**How it works:**

1. Glances collects system metrics (auto-installed, auto-started)
2. GlanceWatch queries Glances API, compares against thresholds
3. Returns HTTP 200 if healthy, HTTP 503 if unhealthy
4. Uptime Kuma monitors the endpoint and sends alerts

---

## Quick Install

### pip (Recommended)
\`\`\`bash
pip install glancewatch
\`\`\`

### Homebrew (macOS/Linux)
\`\`\`bash
brew tap collynes/glancewatch
brew install glancewatch
\`\`\`

### One-liner (Linux/macOS)
\`\`\`bash
curl -sSL https://raw.githubusercontent.com/collynes/glancewatch/main/scripts/install-pip.sh | bash
\`\`\`

---

## The Tech Stack

- **FastAPI 0.115+** — Modern, fast Python web framework
- **Uvicorn 0.30+** — Lightning-fast ASGI server
- **Glances 4.0+** — Cross-platform system monitoring
- **Pydantic 2.10+** — Data validation that actually makes sense
- **httpx 0.27+** — Modern async HTTP client

Why FastAPI? Because I wanted automatic OpenAPI docs, async support, and Python type hints. No Flask boilerplate.

---

## The Features: What You Get

### 1. One-Command Background Service

The installer script detects your system and does the right thing:

\`\`\`bash
curl -sSL https://raw.githubusercontent.com/collynes/glancewatch/main/scripts/install-pip.sh | bash
\`\`\`

**On systemd systems:**
- Creates systemd service
- Enables auto-start on boot
- Restarts on crashes
- Logs to journald

**On non-systemd systems:**
- Uses nohup
- Survives terminal disconnect
- Reports PID for management

No manual intervention. Just works.

### 2. Modern Web Dashboard

Clean, modern interface at http://localhost:8000:

- **Real-time metrics dashboard**
- **System Info Panel** — hostname, OS, Python, uptime
- **Sparkline charts** — visual trend indicators
- **Live threshold configuration**
- **Export to JSON** — download monitoring data
- **Auto-refresh** every 5 seconds
- **Dark/light mode toggle**

### 3. Simple HTTP Health Checks

\`\`\`bash
# Check system health
curl http://localhost:8000/status
# Returns 200 if healthy, 503 if any threshold exceeded

# Individual checks
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl http://localhost:8000/config
\`\`\`

Uptime Kuma monitors these endpoints. When you get a 503, you get an alert. Simple.

### 4. Configurable Thresholds

Default thresholds (80% RAM, 80% CPU, 90% disk), but change them via:

- **Web UI** (pretty interface)
- **REST API** (PUT /config)
- **Config file** (~/.config/glancewatch/config.yaml)
- **Environment variables**

Changes persist. No restart required.

### 5. Auto-Everything

- Auto-installs Glances if missing
- Auto-starts Glances if not running
- Auto-detects Glances API version (v4/v3)
- Auto-detects mount points
- Auto-saves config changes
- Auto-restarts on crashes (systemd mode)

You shouldn't have to think about any of this.

---

## Configuration

Create a \`config.yaml\` file or use environment variables:

\`\`\`yaml
# config.yaml
glances_url: "http://localhost:61208"
port: 8000
thresholds:
  cpu: 80.0
  ram: 80.0
  disk: 90.0
\`\`\`

Or use environment variables:
\`\`\`bash
export GLANCES_URL="http://localhost:61208"
export GLANCEWATCH_PORT=8000
export CPU_THRESHOLD=80
export RAM_THRESHOLD=80
export DISK_THRESHOLD=90
\`\`\`

---

## Uptime Kuma Integration

1. In Uptime Kuma, add a new monitor
2. Select **"HTTP(s) - JSON Query"**
3. Set URL: \`http://your-server:8000/status\`
4. JSON Path: \`$.ok\`
5. Expected Value: \`true\`

When CPU spikes or RAM fills up, Uptime Kuma sends Slack/Discord/Email alerts. Simple.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| \`GET /\` | Web Dashboard |
| \`GET /status\` | JSON status for Uptime Kuma |
| \`GET /health\` | Health check endpoint |
| \`GET /config\` | Current configuration |
| \`GET /metrics\` | Detailed system metrics |
| \`GET /docs\` | Setup documentation |

---

## Docker Deployment

\`\`\`yaml
# docker-compose.yml
version: '3.8'
services:
  glancewatch:
    image: python:3.12-slim
    command: sh -c "pip install glancewatch && glancewatch"
    ports:
      - "8000:8000"
    environment:
      - GLANCES_URL=http://glances:61208
    depends_on:
      - glances

  glances:
    image: nicolargo/glances:latest
    ports:
      - "61208:61208"
    command: glances -w
\`\`\`

---

## The Version History Journey

### v1.0.x: The MVP
- Basic FastAPI app
- Manual Glances management
- Console-only interface

### v1.2.0-1.2.4: Production Ready
- Web UI with router-style design
- Background service automation
- PyPI, Homebrew, npm distribution
- 84% test coverage

### v1.2.5: UI Enhancements
- System Info Panel
- Sparkline mini-charts
- Export functionality
- Dependency updates

### v1.2.6: Bug Fixes
- Glances API v4 compatibility
- Fixed async response handling

---

## The Lessons Learned

### 1. Users Want Simple
Not "simple for developers." Simple for humans.

\`\`\`bash
# Too complex
docker-compose up -d
kubectl apply -f deployment.yaml

# Just right
pip install glancewatch
\`\`\`

### 2. Automatic Is Better Than Manual
Don't tell users to run \`nohup …\` manually. Do it for them.

### 3. Test in Production Environments
Your local dev setup lies to you. Test pip installs in fresh VMs.

### 4. API Versioning Matters
Glances 4.x uses \`/api/4/\`, Glances 3.x uses \`/api/3/\`. Handle both gracefully.

### 5. Logging Is a Feature
Default should be quiet. Add \`--verbose\` for debugging. Respect the terminal.

---

## Code Quality

- **84% test coverage**
- **70+ test cases**
- Tests on Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- Linting (ruff), Type checking (mypy)
- CI/CD with GitHub Actions

---

## Links

- **GitHub**: https://github.com/collynes/glancewatch
- **PyPI**: https://pypi.org/project/glancewatch/
- **Homebrew**: \`brew tap collynes/glancewatch\`
- **Documentation**: https://github.com/collynes/glancewatch/tree/main/docs

---

## Try It Yourself

\`\`\`bash
# Automated installer (recommended)
curl -sSL https://raw.githubusercontent.com/collynes/glancewatch/main/scripts/install-pip.sh | bash

# Or just pip
pip install glancewatch
glancewatch
\`\`\`

**Set up Uptime Kuma monitoring:**
1. Add HTTP(s) - JSON Query monitor
2. URL: \`http://your-server:8000/status\`
3. JSON Path: \`$.ok\`
4. Expected Value: \`true\`
5. Done!

---

## Final Thoughts

I built GlanceWatch because I was tired of complex monitoring setups. I wanted something that:

- Installs fast
- Configures itself
- Runs forever
- Alerts when needed
- **Just works**

If you're monitoring Linux servers and using Uptime Kuma (or similar), give it a try. It's free, open-source, and designed to get out of your way.

**The best tool is the one that just works.**

---

⭐ **Star the repo if you find it useful!**

Found a bug? [Open an issue](https://github.com/collynes/glancewatch/issues)

---

*Made with ❤️ for simple system monitoring*

---

**About the Author**

Collins Kemboi is a software engineer who believes monitoring shouldn't require a PhD. When not building dev tools, he's probably debugging why his homelab is down (again).

---

**Tags:** #Python #DevOps #Monitoring #FastAPI #OpenSource #SystemAdministration #Automation #Linux #ServerMonitoring #UptimeKuma #Glances

---

**Discussion Questions**

1. What's your current server monitoring setup?
2. What's the most annoying part of setting up monitoring?
3. Would you use a tool like this? Why or why not?
4. What features would you want in a monitoring bridge?

Drop your thoughts in the comments!
