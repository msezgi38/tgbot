# Asterisk Configuration Template
# Copy these files to your Asterisk configuration directory
# Default location: /etc/asterisk/

## Files to copy:
- asterisk/configs/pjsip.conf → /etc/asterisk/pjsip.conf
- asterisk/configs/extensions.conf → /etc/asterisk/extensions.conf  
- asterisk/configs/manager.conf → /etc/asterisk/manager.conf

## After copying:
1. Edit pjsip.conf and replace placeholders:
   - YOUR_USERNAME → Your MagnusBilling username
   - YOUR_PASSWORD → Your MagnusBilling password

2. Create custom sounds directory:
   sudo mkdir -p /var/lib/asterisk/sounds/custom

3. Add IVR audio file:
   sudo cp your_audio.wav /var/lib/asterisk/sounds/custom/press_one_ivr.wav

4. Reload Asterisk:
   sudo asterisk -rx "core reload"

5. Verify trunk registration:
   sudo asterisk -rx "pjsip show registrations"
