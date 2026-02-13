---
description: Deploy Press-1 IVR Bot to Debian 12 server
---

# Sunucu Kurulum Rehberi (Debian 12)

SSH ile sunucuya bağlandıktan sonra aşağıdaki komutları sırayla çalıştırın.

---

## Adım 1: Sistem Güncelleme

```bash
apt update && apt upgrade -y
```

---

## Adım 2: Gerekli Paketleri Kur

```bash
apt install -y git python3 python3-pip python3-venv postgresql postgresql-contrib asterisk curl wget nano
```

---

## Adım 3: PostgreSQL Veritabanı Oluştur

```bash
sudo -u postgres psql -c "CREATE USER ivrbot WITH PASSWORD 'IVRBot2026Secure!';"
sudo -u postgres psql -c "CREATE DATABASE ivr_bot OWNER ivrbot;"
```

---

## Adım 4: Projeyi GitHub'dan Çek

```bash
cd /opt
git clone https://github.com/msezgi38/tgbot.git
cd tgbot
```

---

## Adım 5: Veritabanı Şemasını Yükle

```bash
sudo -u postgres psql -d ivr_bot -f /opt/tgbot/database/schema.sql
```

---

## Adım 6: Python Bağımlılıkları

```bash
cd /opt/tgbot
python3 -m venv venv
source venv/bin/activate
pip install python-telegram-bot asyncpg aiohttp fastapi uvicorn panoramisk
```

---

## Adım 7: config.py Ayarlarını Güncelle

```bash
nano /opt/tgbot/bot/config.py
```

Değiştirilecek satırlar:

```python
# Satır 17 - Sunucu IP'nizi yazın:
OXAPAY_WEBHOOK_URL = "http://SUNUCU_IP:8000/webhook/oxapay"

# Satır 34-35 - DB bilgilerini güncelleyin:
"user": "ivrbot",
"password": "IVRBot2026Secure!",

# Satır 94 - Telegram ID'nizi ekleyin:
ADMIN_TELEGRAM_IDS = [SIZIN_TELEGRAM_ID]
```

---

## Adım 8: Mock'tan Gerçek DB'ye Geç

```bash
nano /opt/tgbot/bot/main.py
```

Satır 23'ü değiştirin:

```python
# ESKİ:
from database_mock import db

# YENİ:
from database import db
```

---

## Adım 9: Asterisk Yapılandırması

```bash
# Mevcut config'leri yedekle
cp /etc/asterisk/extensions.conf /etc/asterisk/extensions.conf.backup
cp /etc/asterisk/manager.conf /etc/asterisk/manager.conf.backup
cp /etc/asterisk/pjsip.conf /etc/asterisk/pjsip.conf.backup

# Proje config'lerini kopyala
cp /opt/tgbot/asterisk/configs/extensions.conf /etc/asterisk/extensions.conf
cp /opt/tgbot/asterisk/configs/manager.conf /etc/asterisk/manager.conf
cp /opt/tgbot/asterisk/configs/pjsip.conf /etc/asterisk/pjsip.conf

# Boş pjsip_users.conf oluştur (dinamik olarak doldurulacak)
touch /etc/asterisk/pjsip_users.conf

# pjsip.conf'a include satırı ekle
echo '#include pjsip_users.conf' >> /etc/asterisk/pjsip.conf

# Asterisk'i yeniden başlat
systemctl restart asterisk
```

---

## Adım 10: Servisleri Başlat

### Terminal 1 - Telegram Bot:
```bash
cd /opt/tgbot
source venv/bin/activate
cd bot
python3 main.py
```

### Terminal 2 - Webhook Server:
```bash
cd /opt/tgbot
source venv/bin/activate
cd dialer
python3 webhook_server.py
```

### Terminal 3 - Campaign Worker:
```bash
cd /opt/tgbot
source venv/bin/activate
cd dialer
python3 campaign_worker.py
```

---

## Adım 11: Test Et

1. Telegram'da @callnowp1_bot'a gidin
2. /start yazın
3. Dashboard görünmeli ✅

---

## Adım 12 (Opsiyonel): PM2 ile Arka Planda Çalıştır

```bash
apt install -y npm
npm install -g pm2

cd /opt/tgbot
pm2 start "venv/bin/python3 bot/main.py" --name "tgbot"
pm2 start "venv/bin/python3 dialer/webhook_server.py" --name "webhook"
pm2 start "venv/bin/python3 dialer/campaign_worker.py" --name "worker"
pm2 save
pm2 startup
```

---

## Özet - Açılması Gereken Portlar

| Port | Servis | Yön |
|------|--------|-----|
| 8000 | Webhook Server (FastAPI) | İçeri (Oxapay + Asterisk) |
| 5060 | SIP (PJSIP) | İçeri/Dışarı |
| 5038 | Asterisk AMI | Sadece localhost |
