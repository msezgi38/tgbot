# 📞 Spooficon Press One - Vicidial Telegram Bot

**Professional Press-1 IVR Campaign Management via Telegram**

Modern Telegram interface for Vicidial campaigns with AMD (Answering Machine Detection) support, real-time statistics, and caller ID management.

---

## � Features

### ✨ Campaign Management
- 🚀 **Launch Campaigns** - Create and start campaigns from Telegram
- 📊 **Live Statistics** - Real-time campaign monitoring
- ⏸️ **Pause/Resume** - Full campaign control
- 📋 **Call Logs** - Detailed call results with timestamps

### 🎤 IVR & Audio
- 🎙️ **Voice Upload** - Upload IVR messages directly from Telegram
- 🤖 **AMD Support** - Answering Machine Detection via Vicidial
- 📂 **Audio Library** - Save and reuse voice files
- 🔊 **Format Support** - MP3, WAV, OGG, Voice Messages

### 📞 Caller ID Management
- 🔧 **Configure CID** - Set caller identification
- 📋 **Preset CIDs** - Verified, high-performance numbers
- ✏️ **Custom CID** - Use your own numbers with validation
- 🛡️ **Blacklist Check** - Automatic compliance verification

### 💰 Balance & Credits
- 💵 **Balance Tracking** - Real-time credit monitoring
- 📈 **Usage Stats** - Lines used, calls made
- 💳 **Payment Integration** - Crypto payments via Oxapay (optional)

### 📱 Professional Interface
- 🎨 **Modern UI** - Clean, intuitive Telegram interface
- 📊 **Rich Statistics** - Progress bars, charts, detailed metrics
- 🔔 **Smart Notifications** - Campaign updates and alerts
- 🌐 **Multi-language Ready** - Easy localization support

---

## 🏗️ Architecture

```
Telegram Bot (Interface)
         ↓
    AMI + MySQL
         ↓
   Vicidial (Engine)
         ↓
   Asterisk + AMD
```

**Vicidial as Backend:**
- ✅ Uses existing Vicidial installation
- ✅ Minimal changes to Vicidial
- ✅ Leverages proven AMD system
- ✅ Full Asterisk integration

---

## 📋 Requirements

### System Requirements
- **OS:** AlmaLinux 8/9, Rocky Linux, CentOS 7/8, Ubuntu 20.04+
- **Python:** 3.11+
- **RAM:** 2 GB minimum, 4 GB recommended
- **Disk:** 10 GB free space

### Vicidial Requirements
- **Vicidial:** 2.14+
- **Asterisk:** 13/16/18
- **MySQL/MariaDB:** 5.7+/ 10.3+
- **AMI Access:** Enabled
- **Database Access:** Read/Write permissions

### Python Dependencies
```bash
python-telegram-bot >= 20.0
pymysql >= 1.0.2
asterisk-ami >= 0.1.5
python-dotenv >= 1.0.0
```

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
cd /opt
git clone https://github.com/yourusername/tgbot.git
cd tgbot
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Bot
```bash
cp config.example.py config.py
nano config.py
```

**Required Settings:**
```python
# Telegram
TELEGRAM_BOT_TOKEN = "your_bot_token_here"

# Vicidial Database
VICIDIAL_DB_HOST = "localhost"
VICIDIAL_DB_NAME = "asterisk"
VICIDIAL_DB_USER = "cron"
VICIDIAL_DB_PASS = "your_password"

# Asterisk AMI
AMI_HOST = "127.0.0.1"
AMI_PORT = 5038
AMI_USER = "cron"
AMI_PASS = "your_ami_password"
```

### 4. Run Bot
```bash
# Test mode
python bot/main.py

# Production (with systemd)
sudo systemctl enable tgbot
sudo systemctl start tgbot
```

---

## 🔧 Installation (Detailed)

### Step 1: Prepare Vicidial Server
```bash
# Install Python 3.11
sudo dnf install python3.11 python3.11-pip -y

# Create bot user (optional)
sudo useradd -m -s /bin/bash tgbot
```

### Step 2: Clone & Setup
```bash
cd /opt
git clone https://github.com/yourusername/tgbot.git
cd tgbot

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Database Permissions
```sql
-- Grant bot database access
GRANT SELECT, INSERT, UPDATE ON asterisk.vicidial_campaigns TO 'tgbot'@'localhost' IDENTIFIED BY 'botpass123';
GRANT SELECT, INSERT ON asterisk.vicidial_lists TO 'tgbot'@'localhost';
GRANT SELECT ON asterisk.vicidial_log TO 'tgbot'@'localhost';
GRANT SELECT ON asterisk.vicidial_campaign_stats TO 'tgbot'@'localhost';
FLUSH PRIVILEGES;
```

### Step 4: AMI Configuration
```bash
# Edit /etc/asterisk/manager.conf
sudo nano /etc/asterisk/manager.conf
```

Add:
```ini
[tgbot]
secret = tgbot123
deny=0.0.0.0/0.0.0.0
permit=127.0.0.1/255.255.255.255
read = system,call,log,verbose,command,agent,user,reporting
write = system,call,command,agent,user
```

```bash
# Reload AMI
sudo asterisk -rx "manager reload"
```

### Step 5: Configure Bot
```bash
cp config.example.py config.py
nano config.py
```

### Step 6: Test Connection
```bash
# Test database
python -c "from bot.vicidial_connector import test_connection; test_connection()"

# Test AMI
python -c "from bot.ami_connector import test_ami; test_ami()"
```

### Step 7: Run Bot
```bash
python bot/main.py
```

---

## 🔄 Systemd Service (Auto-start)

Create service file:
```bash
sudo nano /etc/systemd/system/tgbot.service
```

```ini
[Unit]
Description=Telegram Vicidial Bot
After=network.target mysql.service asterisk.service

[Service]
Type=simple
User=tgbot
WorkingDirectory=/opt/tgbot
Environment="PATH=/opt/tgbot/venv/bin"
ExecStart=/opt/tgbot/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot
sudo systemctl start tgbot
sudo systemctl status tgbot
```

---

## � Usage

### Starting the Bot
1. Open Telegram
2. Search for your bot: `@YourBotName`
3. Send `/start`

### Creating a Campaign
1. Click **🚀 Launch Campaign**
2. Enter campaign name
3. Upload IVR voice message
4. Upload CSV with phone numbers
5. Configure AMD settings (optional)
6. Launch!

### Managing Campaigns
- **📊 Live Statistics** - View real-time stats
- **⏸️ Pause/Resume** - Control campaigns
- **📋 Call Logs** - Detailed call results
- **🔧 Configure CID** - Set caller ID

---

## 🎯 Vicidial Integration

### Campaign Creation
Bot creates campaigns in Vicidial with prefix `TG_`:
```sql
INSERT INTO vicidial_campaigns (
    campaign_id, campaign_name, active,
    dial_method, amd_send_to_vmx
) VALUES (
    'TG_001', 'Product Launch', 'Y',
    'RATIO', 'Y'
);
```

### AMD Configuration
Campaigns automatically use Vicidial's AMD:
- **Detect Answering Machines**
- **Leave Messages on VM**
- **Skip to Next Call**
- **Configurable via Telegram**

### Call Logs
Real-time call results from `vicidial_log`:
- ✅ Pressed 1 (Success)
- 📞 Answered (No press)
- 🤖 Voicemail Detected
- ⭕ No Answer
- ❌ Failed/Busy

---

## � Security

### Best Practices
1. **Separate DB User** - Create dedicated bot user
2. **Read-Only Start** - Test with SELECT permissions first
3. **AMI Restrictions** - Limit to localhost
4. **Campaign Prefix** - Only touch `TG_` campaigns
5. **Backup First** - Always backup before changes

### Firewall
```bash
# Bot doesn't need external ports
# Only Telegram API (HTTPS outbound)
```

---

## 🐛 Troubleshooting

### Bot Won't Start
```bash
# Check logs
journalctl -u tgbot -f

# Verify Python
python3.11 --version

# Test dependencies
pip list | grep telegram
```

### Database Connection Failed
```bash
# Test MySQL access
mysql -u tgbot -p asterisk

# Check grants
SHOW GRANTS FOR 'tgbot'@'localhost';
```

### AMI Connection Failed
```bash
# Check AMI status
sudo asterisk -rx "manager show connected"

# Verify credentials in manager.conf
sudo cat /etc/asterisk/manager.conf | grep tgbot -A 5
```

### Campaign Not Starting
```bash
# Check Asterisk
sudo asterisk -rx "core show channels"

# Verify campaign in DB
mysql -u root -p asterisk -e "SELECT * FROM vicidial_campaigns WHERE campaign_id LIKE 'TG_%'"
```

---

## � Project Structure

```
tgbot/
├── bot/
│   ├── main.py                    # Main bot application
│   ├── config.py                  # Configuration
│   ├── vicidial_connector.py      # Vicidial DB integration
│   ├── ami_connector.py           # Asterisk AMI
│   ├── campaign_manager.py        # Campaign CRUD
│   ├── ui_components.py           # Telegram UI helpers
│   └── database_mock.py           # Mock DB for testing
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── systemd/
    └── tgbot.service              # Systemd service file
```

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Vicidial** - Powerful open-source contact center suite
- **python-telegram-bot** - Excellent Telegram API wrapper
- **Asterisk** - The world's leading open-source PBX

---

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/tgbot/issues)
- **Telegram:** @YourSupportChannel
- **Email:** support@yourdomain.com

---

## 🗺️ Roadmap

- [x] Basic Vicidial integration
- [x] Campaign management
- [x] AMD support
- [x] Caller ID management
- [ ] Advanced reporting
- [ ] Multi-tenant support
- [ ] Web dashboard
- [ ] API endpoints
- [ ] Mobile app

---

**Built with ❤️ for Vicidial Community**
