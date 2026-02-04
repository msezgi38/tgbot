# Quick Start Guide - Press-1 IVR Bot

## 🎯 What Was Built

A complete SaaS "Press-1 IVR Bot" system where:
- Users interact via **Telegram**
- Pay with **cryptocurrency** (Oxapay)
- Upload phone lists via **CSV**
- System dials via **Asterisk → MagnusBilling → PSTN**
- Detects when recipients **press '1'**
- Tracks results in **PostgreSQL**

## 📂 Project Structure

```
c:\Users\msila\Desktop\tgbot\
│
├── asterisk/                      # Asterisk PBX Configuration
│   ├── configs/
│   │   ├── pjsip.conf            # ⚠️ MagnusBilling trunk (UPDATE CREDENTIALS)
│   │   ├── extensions.conf       # ✅ Press-1 IVR dialplan
│   │   └── manager.conf          # ✅ AMI access config
│   ├── sounds/                    # (Create this directory)
│   │   └── press_one_ivr.wav     # ⚠️ You need to create this audio file
│   └── README.txt
│
├── bot/                          # Telegram Bot Application
│   ├── main.py                   # ✅ Bot with all commands
│   ├── database.py               # ✅ PostgreSQL ORM
│   ├── oxapay_handler.py         # ✅ Payment integration
│   ├── config.py                 # ⚠️ UPDATE DATABASE PASSWORD
│   └── requirements.txt          # Python dependencies
│
├── dialer/                       # Call Processing Engine
│   ├── ami_client.py             # ✅ Asterisk AMI connection
│   ├── campaign_worker.py        # ✅ Call execution loop
│   ├── webhook_server.py         # ✅ DTMF event receiver
│   └── requirements.txt          # Python dependencies
│
├── database/
│   └── schema.sql                # ✅ PostgreSQL database schema
│
├── README.md                     # Full documentation
├── example_numbers.csv           # CSV format example
│
└── This directory structure
```

## ⚡ Super Quick Start (5 Steps)

### 1. Install Python Dependencies

```bash
# Navigate to project
cd c:\Users\msila\Desktop\tgbot

# Install bot dependencies
pip install -r bot\requirements.txt

# Install dialer dependencies
pip install -r dialer\requirements.txt
```

### 2. Setup PostgreSQL Database

```bash
# Create database (using psql or pgAdmin)
psql -U postgres -c "CREATE DATABASE ivr_bot;"

# Import schema
psql -U postgres -d ivr_bot -f database\schema.sql
```

### 3. Configure Credentials

#### A. Update `bot\config.py`
```python
DATABASE_CONFIG = {
    "password": "your_actual_db_password",  # ⚠️ CHANGE THIS
}

ADMIN_TELEGRAM_IDS = [123456789]  # ⚠️ Your Telegram user ID
```

#### B. Update `asterisk\configs\pjsip.conf`
```ini
username=YOUR_MAGNUSBILLING_USERNAME  # ⚠️ CHANGE THIS
password=YOUR_MAGNUSBILLING_PASSWORD  # ⚠️ CHANGE THIS
```

### 4. Deploy Asterisk Configs (Linux only)

```bash
# Copy configs
sudo cp asterisk/configs/* /etc/asterisk/

# Reload Asterisk
sudo asterisk -rx "core reload"

# Verify trunk registration
sudo asterisk -rx "pjsip show registrations"
# Should show: magnus_trunk ... Registered
```

### 5. Start All Services

**Terminal 1: Webhook Server**
```bash
cd dialer
python webhook_server.py
```

**Terminal 2: Campaign Worker**
```bash
cd dialer
python campaign_worker.py
```

**Terminal 3: Telegram Bot**
```bash
cd bot
python main.py
```

## 🎮 Using the Bot

1. **Find your bot** on Telegram (use the token to get @username)
2. Send `/start`
3. Use `/buy` to purchase credits
4. Use `/new_campaign` to create a campaign
5. Upload CSV file with phone numbers
6. Click "Start Campaign"
7. Monitor with `/campaigns`

## ⚠️ Critical TODOs Before Running

- [ ] Get MagnusBilling credentials (username, password)
- [ ] Update `pjsip.conf` with credentials
- [ ] Update `config.py` with database password
- [ ] Create IVR audio file (`press_one_ivr.wav`)
- [ ] Install Asterisk if not already installed
- [ ] Deploy Asterisk configs
- [ ] Verify trunk registration

## 🧪 Quick Tests

### Test Database Connection
```bash
psql -U postgres -d ivr_bot -c "SELECT 1;"
```

### Test Asterisk Trunk
```bash
sudo asterisk -rx "pjsip show endpoints"
sudo asterisk -rx "pjsip show registrations"
```

### Test Webhook Server
```bash
curl http://localhost:8000/
# Should return: {"service":"IVR Bot Webhook Server","status":"running"}
```

### Test Bot (Once Running)
- Send `/start` to your bot
- Check database: `psql -U postgres -d ivr_bot -c "SELECT * FROM users;"`

## 📞 Sample CSV Format

Create `test_numbers.csv`:
```csv
1234567890
9876543210
5555555555
```

## 🆘 Quick Troubleshooting

**Trunk not registering?**
→ Check credentials in `pjsip.conf`
→ Check firewall allows port 5060
→ Verify MagnusBilling account is active

**Bot not starting?**
→ Check database credentials in `config.py`
→ Ensure PostgreSQL is running
→ Verify bot token is correct

**Calls not originating?**
→ Check AMI connection: `sudo asterisk -rx "manager show connected"`
→ Verify campaign worker is running
→ Check user has sufficient credits

**DTMF not detected?**
→ Verify webhook server is running on port 8000
→ Check Asterisk can reach `localhost:8000`
→ Look for webhook logs

## 📚 Full Documentation

See [`README.md`](file:///c:/Users/msila/Desktop/tgbot/README.md) for:
- Detailed installation steps
- Asterisk setup guide
- Audio file creation
- Production deployment
- Security hardening
- Complete troubleshooting guide

## 🎯 Next Steps After Setup

1. **Create test campaign** with 1-2 numbers
2. **Monitor logs** in all 3 terminals
3. **Check database** for call records
4. **Verify billing** deductions work
5. **Test payment flow** with small amount
6. **Scale up** once everything works

## 🔐 Security Reminder

Before production:
- Change AMI password in `manager.conf`
- Use strong database password
- Setup HTTPS for webhooks
- Restrict AMI to localhost only
- Use environment variables for secrets

---

**Status:** ✅ All code delivered
**Next:** Configure credentials and test!

For support, see the main [README.md](file:///c:/Users/msila/Desktop/tgbot/README.md)
