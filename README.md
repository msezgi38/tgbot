# Press-1 IVR Bot - SaaS Solution

Complete Telegram-based SaaS for automated Press-1 IVR campaigns. Users pay with cryptocurrency, upload contact lists, and get real-time campaign results.

## 🏗️ Architecture

```
Telegram User → Bot → Oxapay (Payment) → PostgreSQL
                ↓
         Campaign Worker → AMI → Asterisk → MagnusBilling → PSTN
                ↓                    ↓
         Webhook Server ← DTMF ←─────┘
```

## ⚡ Features

- ✅ **Telegram Bot Interface** - Easy campaign management via chat
- ✅ **Crypto Payments** - Oxapay integration (USDT, BTC, ETH)
- ✅ **Automated Dialing** - Asterisk AMI with MagnusBilling trunk
- ✅ **DTMF Detection** - Track when users press '1'
- ✅ **Real-time Stats** - Campaign progress tracking
- ✅ **Credit System** - Fair usage billing (1 credit = 1 minute)

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows with WSL
- **Python**: 3.9+
- **PostgreSQL**: 12+
- **Asterisk**: 16+ with PJSIP
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB+

### Accounts Needed
1. **MagnusBilling Account** - SIP trunk provider
2. **Oxapay Account** - Crypto payment gateway
3. **Telegram Bot Token** - From @BotFather

## 🚀 Installation

### Step 1: Clone & Setup

```bash
# Navigate to project directory
cd c:/Users/msila/Desktop/tgbot

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install bot dependencies
pip install -r bot/requirements.txt

# Install dialer dependencies
pip install -r dialer/requirements.txt
```

### Step 2: Database Setup

```bash
# Install PostgreSQL (if not already installed)
# Windows: Download from https://www.postgresql.org/download/windows/
# Linux: sudo apt-get install postgresql

# Create database
psql -U postgres
CREATE DATABASE ivr_bot;
\q

# Import schema
psql -U postgres -d ivr_bot -f database/schema.sql
```

### Step 3: Asterisk Configuration

#### Install Asterisk (Linux)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install asterisk

# CentOS/RHEL
sudo yum install asterisk

# Start Asterisk
sudo systemctl start asterisk
sudo systemctl enable asterisk
```

#### Configure Asterisk

```bash
# Backup existing configs
sudo cp /etc/asterisk/pjsip.conf /etc/asterisk/pjsip.conf.backup
sudo cp /etc/asterisk/extensions.conf /etc/asterisk/extensions.conf.backup
sudo cp /etc/asterisk/manager.conf /etc/asterisk/manager.conf.backup

# Copy new configs
sudo cp asterisk/configs/pjsip.conf /etc/asterisk/
sudo cp asterisk/configs/extensions.conf /etc/asterisk/
sudo cp asterisk/configs/manager.conf /etc/asterisk/

# Edit pjsip.conf with YOUR MagnusBilling credentials
sudo nano /etc/asterisk/pjsip.conf
# Replace:
#   YOUR_USERNAME with your MagnusBilling username
#   YOUR_PASSWORD with your MagnusBilling password

# Create custom sounds directory
sudo mkdir -p /var/lib/asterisk/sounds/custom

# Copy IVR audio (you need to create this)
# Example: Use text-to-speech to generate "Press 1 if you're interested"
# sudo cp your_audio.wav /var/lib/asterisk/sounds/custom/press_one_ivr.wav

# Reload Asterisk
sudo asterisk -rx "core reload"

# Check trunk registration
sudo asterisk -rx "pjsip show registrations"
# Should show: magnus_trunk ... Registered

# Check AMI
sudo asterisk -rx "manager show users"
# Should show: ivr_bot
```

### Step 4: Configure Bot

Edit `bot/config.py`:

```python
# Update database credentials
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ivr_bot",
    "user": "postgres",
    "password": "YOUR_DB_PASSWORD",  # ⚠️ UPDATE THIS
}

# Update webhook URL (for production)
OXAPAY_WEBHOOK_URL = "https://your-domain.com/webhook/oxapay"  # ⚠️ UPDATE THIS

# Update admin Telegram IDs
ADMIN_TELEGRAM_IDS = [123456789]  # ⚠️ UPDATE WITH YOUR TELEGRAM ID
```

### Step 5: Create IVR Audio

You need an audio file for the IVR message. Options:

**Option 1: Text-to-Speech (Free)**
```bash
# Using Google TTS (Python)
pip install gTTS
python -c "from gtts import gTTS; tts = gTTS('Press 1 if you are interested', lang='en'); tts.save('press_one_ivr.mp3')"

# Convert to WAV (requires ffmpeg)
ffmpeg -i press_one_ivr.mp3 -ar 8000 -ac 1 press_one_ivr.wav

# Copy to Asterisk
sudo cp press_one_ivr.wav /var/lib/asterisk/sounds/custom/
```

**Option 2: Record Your Own**
- Record a 5-10 second message
- Convert to: 8kHz, mono, WAV format
- Copy to `/var/lib/asterisk/sounds/custom/press_one_ivr.wav`

## 🎮 Running the System

### Terminal 1: Webhook Server
```bash
cd dialer
python webhook_server.py
# Should show: Webhook server started on http://0.0.0.0:8000
```

### Terminal 2: Campaign Worker
```bash
cd dialer
python campaign_worker.py
# Should show: 
#   ✅ Database connected
#   ✅ Connected to Asterisk AMI
#   ✅ Campaign Worker started successfully
```

### Terminal 3: Telegram Bot
```bash
cd bot
python main.py
# Should show:
#   ✅ Database connected
#   ✅ Bot initialized
#   🚀 Starting Press-1 IVR Bot...
```

## 📱 Using the Bot

### 1. Start Bot
- Open Telegram
- Search for your bot (use token to find @username)
- Send `/start`

### 2. Buy Credits
- Use `/buy` command
- Select a package
- Pay with cryptocurrency via Oxapay
- Credits added automatically

### 3. Create Campaign
- Use `/new_campaign`
- Enter campaign name
- Upload CSV file with phone numbers:
  ```csv
  1234567890
  9876543210
  ```
- Click "Start Campaign"

### 4. Monitor Progress
- Use `/campaigns` to see all campaigns
- View real-time statistics
- Check `/balance` for remaining credits

## 🧪 Testing

### Test Trunk Registration
```bash
sudo asterisk -rx "pjsip show registrations"
# Should show: magnus_trunk    sip.1337global.sbs    Registered
```

### Test Manual Call
```bash
sudo asterisk -rx "channel originate PJSIP/1234567890@magnus_trunk application Playback hello-world"
# Should initiate a test call
```

### Test AMI Connection
```bash
telnet localhost 5038
# Enter:
Action: Login
Username: ivr_bot
Secret: IVRBot@Secure2026!

# Should respond: Response: Success
```

### Test Database
```bash
psql -U postgres -d ivr_bot
SELECT * FROM users;
SELECT * FROM campaigns;
\q
```

## 🔧 Troubleshooting

### Asterisk trunk not registering
```bash
# Check Asterisk logs
sudo asterisk -rx "pjsip show registrations"
sudo tail -f /var/log/asterisk/full

# Common issues:
# 1. Wrong credentials in pjsip.conf
# 2. Firewall blocking port 5060
# 3. MagnusBilling account not active
```

### Calls not originating
```bash
# Check AMI connection
sudo asterisk -rx "manager show connected"

# Check active channels
sudo asterisk -rx "core show channels"

# Check if budget/credits: Check MagnusBilling dashboard
```

### Webhook not receiving DTMF
```bash
# Test webhook manually
curl -X POST http://localhost:8000/dtmf_webhook \
  -H "Content-Type: application/json" \
  -d '{"call_id":"test123","destination":"1234567890","dtmf_pressed":1}'

# Check webhook server logs
# Should show: 📨 Webhook received: ...
```

### Database connection errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U postgres -d ivr_bot -c "SELECT 1"

# Check credentials in config.py
```

## 💳 Oxapay Webhook Setup

For production, you need a **public HTTPS URL** for Oxapay webhooks.

### Option 1: ngrok (Testing)
```bash
ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update config.py: OXAPAY_WEBHOOK_URL = "https://abc123.ngrok.io/webhook/oxapay"
```

### Option 2: Production Server
- Deploy to VPS with domain
- Setup HTTPS (Let's Encrypt)
- Update `OXAPAY_WEBHOOK_URL` in config.py
- Configure firewall to allow port 8000

## 📊 System Architecture Details

### Call Flow
1. **User starts campaign** via Telegram
2. **Campaign worker** fetches pending numbers
3. **AMI client** sends Originate action to Asterisk
4. **Asterisk** dials via `PJSIP/{number}@magnus_trunk`
5. **MagnusBilling** routes call to PSTN
6. **IVR plays** audio message
7. **User presses '1'** → DTMF detected
8. **Asterisk sends webhook** to Python
9. **Webhook server** updates database
10. **Credits deducted** from user account

### Billing Logic
- **6-second minimum** billing
- **6-second increments** (standard telecom)
- **1 credit = 1 minute** (default)
- Costs calculated on answered calls only

## 🛡️ Security Notes

- ⚠️ **Change default passwords** in `manager.conf`
- ⚠️ **Use HTTPS** for production webhooks
- ⚠️ **Firewall** AMI port 5038 (only localhost)
- ⚠️ **Secure database** with strong password
- ⚠️ **Keep API keys** in environment variables for production

## 📝 File Structure

```
tgbot/
├── asterisk/
│   ├── configs/
│   │   ├── pjsip.conf          # MagnusBilling trunk
│   │   ├── extensions.conf     # IVR dialplan
│   │   └── manager.conf        # AMI config
│   └── sounds/
│       └── press_one_ivr.wav   # IVR audio
├── bot/
│   ├── main.py                 # Telegram bot
│   ├── database.py             # Database ORM
│   ├── oxapay_handler.py       # Payment integration
│   ├── config.py               # Configuration
│   └── requirements.txt
├── dialer/
│   ├── ami_client.py           # AMI connection
│   ├── campaign_worker.py      # Call processor
│   ├── webhook_server.py       # DTMF handler
│   └── requirements.txt
├── database/
│   └── schema.sql              # PostgreSQL schema
└── README.md
```

## 🚀 Production Deployment

### Using Systemd (Linux)

Create service files:

**`/etc/systemd/system/ivr-webhook.service`:**
```ini
[Unit]
Description=IVR Bot Webhook Server
After=network.target postgresql.service asterisk.service

[Service]
Type=simple
User=ivrbot
WorkingDirectory=/path/to/tgbot/dialer
ExecStart=/path/to/tgbot/venv/bin/python webhook_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/ivr-worker.service`:**
```ini
[Unit]
Description=IVR Bot Campaign Worker
After=network.target postgresql.service asterisk.service ivr-webhook.service

[Service]
Type=simple
User=ivrbot
WorkingDirectory=/path/to/tgbot/dialer
ExecStart=/path/to/tgbot/venv/bin/python campaign_worker.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/ivr-bot.service`:**
```ini
[Unit]
Description=IVR Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=ivrbot
WorkingDirectory=/path/to/tgbot/bot
ExecStart=/path/to/tgbot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ivr-webhook ivr-worker ivr-bot
sudo systemctl start ivr-webhook ivr-worker ivr-bot
sudo systemctl status ivr-webhook ivr-worker ivr-bot
```

## 📄 License

This is a commercial SaaS solution. All rights reserved.

## 🤝 Support

For issues or questions, contact your system administrator.

---

**Built with**: Python, Asterisk, PostgreSQL, Telegram Bot API
**Powered by**: MagnusBilling, Oxapay
