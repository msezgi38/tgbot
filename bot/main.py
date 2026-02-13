# =============================================================================
# Telegram Bot - Main Application (User-Scoped PJSIP)
# =============================================================================
# Press-1 IVR Bot - Per-user trunk, lead, and campaign management
# =============================================================================

import logging
import csv
import io
import asyncio
import subprocess
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import TELEGRAM_BOT_TOKEN, CREDIT_PACKAGES, ADMIN_TELEGRAM_IDS, TEST_MODE, SUPPORTED_COUNTRY_CODES, ASTERISK_RELOAD_CMD
# Real PostgreSQL database - data persists across restarts
from database import db
from oxapay_handler import oxapay
from ui_components import ui

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# =============================================================================
# Command Handlers
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Show professional dashboard"""
    user = update.effective_user
    user_data = await db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    stats = await db.get_user_stats(user.id)
    
    dashboard_text = f"""
<b>1337 Press One</b>

Hello {user.first_name or 'User'}, welcome to the advanced press-one system.

<b>Your Settings</b>
Country Code: {user_data.get('country_code', '+1')} | Caller ID: {user_data.get('caller_id', 'Not Set')}

<b>Account & System Info</b>
Balance: ${user_data.get('credits', 0):.2f} | Trunks: {stats.get('trunk_count', 0)} | Leads: {stats.get('lead_count', 0)}
Campaigns: {stats.get('campaign_count', 0)} | Total Calls: {user_data.get('total_calls', 0)}

Ready to launch your campaign?
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch"),
            InlineKeyboardButton("💰 Check Balance", callback_data="menu_balance")
        ],
        [
            InlineKeyboardButton("🔌 My Trunks", callback_data="menu_trunks"),
            InlineKeyboardButton("📋 My Leads", callback_data="menu_leads")
        ],
        [
            InlineKeyboardButton("🔧 Configure CID", callback_data="menu_configure_cid"),
            InlineKeyboardButton("📊 Live Statistics", callback_data="menu_statistics")
        ],
        [
            InlineKeyboardButton("🛠️ Tools & Utilities", callback_data="menu_tools"),
            InlineKeyboardButton("🎵 My Voices", callback_data="menu_voices")
        ],
        [
            InlineKeyboardButton("🔑 Account Info", callback_data="menu_account"),
            InlineKeyboardButton("💬 Support", callback_data="menu_support")
        ]
    ]
    
    # Add admin panel button for admins
    if user.id in ADMIN_TELEGRAM_IDS:
        keyboard.append([
            InlineKeyboardButton("🛡️ Admin Panel", callback_data="menu_admin")
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        dashboard_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    user = update.effective_user
    stats = await db.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("❌ Use /start first.")
        return
    
    credits = stats['credits']
    if credits > 100: credit_status = "🟢 Excellent"
    elif credits > 50: credit_status = "🟡 Good"
    elif credits > 10: credit_status = "🟠 Low"
    else: credit_status = "🔴 Critical"
    
    balance_text = f"""
💰 <b>Account Balance</b>

<b>Status:</b> {credit_status}
<b>Available Credits:</b> {credits:.2f}

<b>Account Statistics:</b>
💵 Total Spent: ${stats['total_spent']:.2f}
📞 Total Calls: {stats['total_calls']}
📊 Campaigns: {stats['campaign_count']}
🔌 SIP Trunks: {stats.get('trunk_count', 0)}
📋 Lead Lists: {stats.get('lead_count', 0)}

💡 1 credit ≈ 1 minute of calling
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Buy Credits", callback_data="menu_buy")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(balance_text, parse_mode='HTML', reply_markup=reply_markup)


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command"""
    buy_text = "💳 <b>Purchase Credits</b>\n\n"
    keyboard = []
    
    for package_id, pkg in CREDIT_PACKAGES.items():
        buy_text += f"📦 {pkg['credits']} Credits — ${pkg['price']} {pkg['currency']}\n"
        keyboard.append([InlineKeyboardButton(
            f"Select {pkg['credits']} Credits",
            callback_data=f"buy_{package_id}"
        )])
    
    buy_text += "\n✅ Secure payments via Oxapay\n✅ Instant delivery"
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(buy_text, parse_mode='HTML', reply_markup=reply_markup)


async def new_campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new_campaign command"""
    context.user_data['creating_campaign'] = True
    context.user_data['campaign_step'] = 'name'
    
    await update.message.reply_text(
        "📝 <b>Create New Campaign</b>\n\nStep 1: Enter campaign name\n\nExample: Product Launch 2026",
        parse_mode='HTML'
    )


async def campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /campaigns command"""
    user = update.effective_user
    user_data = await db.get_or_create_user(user.id)
    campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
    
    if not campaigns:
        await update.message.reply_text(
            "📂 <b>No Campaigns</b>\n\nYou haven't created any campaigns yet.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )
        return
    
    text = "📊 <b>My Campaigns</b>\n\n"
    keyboard = []
    for camp in campaigns:
        status_emoji = {'running': '🟢', 'paused': '🟡', 'completed': '✅', 'failed': '❌'}.get(camp.get('status', ''), '⚪')
        trunk = camp.get('trunk_name', 'No Trunk')
        lead = camp.get('lead_name', 'Direct Upload')
        text += f"{status_emoji} <b>{camp['name']}</b>\n   📞 {camp.get('completed', 0)}/{camp.get('total_numbers', 0)} | 🔌 {trunk}\n\n"
        keyboard.append([InlineKeyboardButton(f"📊 {camp['name'][:25]}", callback_data=f"details_{camp['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
❓ <b>Help & Support</b>

<b>Commands:</b>
/start - Main dashboard
/balance - Check credits
/buy - Purchase credits
/new_campaign - Create campaign
/campaigns - View campaigns
/help - This help

<b>Campaign Creation Flow:</b>
1. 🚀 Launch Campaign
2. Enter campaign name
3. Select IVR voice file
4. Select SIP trunk
5. Select lead list
6. Start campaign!

<b>Key Features:</b>
• 🔌 Per-user SIP trunks (add your own)
• 📋 Reusable lead lists
• 🔧 Custom Caller ID
• 📊 Real-time campaign statistics
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ])
    )


# =============================================================================
# Buy Callback
# =============================================================================

async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy package callback"""
    query = update.callback_query
    await query.answer()
    
    package_id = query.data.replace("buy_", "")
    
    if package_id not in CREDIT_PACKAGES:
        await query.edit_message_text("❌ Invalid package.")
        return
    
    package = CREDIT_PACKAGES[package_id]
    user = update.effective_user
    user_data = await db.get_or_create_user(user.id)
    
    try:
        payment = await oxapay.create_payment(
            amount=package['price'],
            currency=package['currency'],
            order_id=f"user_{user_data['id']}_{package_id}",
            description=f"{package['credits']} credits for {user.username or user.id}"
        )
        
        if payment and payment.get('success'):
            await db.create_payment(
                user_id=user_data['id'],
                track_id=payment['track_id'],
                amount=package['price'],
                credits=package['credits'],
                currency=package['currency'],
                payment_url=payment.get('payment_url', '')
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Pay Now", url=payment.get('payment_url', ''))],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
            ]
            
            await query.edit_message_text(
                f"💳 <b>Payment Created</b>\n\n"
                f"Package: {package['credits']} Credits\n"
                f"Amount: ${package['price']} {package['currency']}\n\n"
                f"Click 'Pay Now' to complete your payment.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            error = payment.get('error', 'Unknown error') if payment else 'No response'
            logger.error(f"❌ Oxapay payment failed: {error}")
            await query.edit_message_text(f"❌ Payment failed: {error}")
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await query.edit_message_text(f"❌ Error: {e}")


# =============================================================================
# Message Handler (Campaign creation + Trunk/Lead input)
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during campaign creation and trunk/lead setup"""
    user = update.effective_user
    
    # --- Handle custom CID input ---
    if context.user_data.get('awaiting_custom_cid'):
        cid = update.message.text.strip()
        is_valid, message = await db.validate_cid(cid)
        
        if is_valid:
            clean_cid = ''.join(filter(str.isdigit, cid))
            await db.set_caller_id(user.id, clean_cid)
            context.user_data['awaiting_custom_cid'] = False
            await update.message.reply_text(
                f"✅ <b>CID Set:</b> {clean_cid}",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]])
            )
        else:
            await update.message.reply_text(f"❌ {message}\n\nTry again or /cancel.", parse_mode='HTML')
        return
    
    # --- Handle admin price editing ---
    if context.user_data.get('editing_price') and user.id in ADMIN_TELEGRAM_IDS:
        pkg_id = context.user_data['editing_price']
        try:
            new_price = float(update.message.text.strip())
            if pkg_id in CREDIT_PACKAGES:
                CREDIT_PACKAGES[pkg_id]['price'] = new_price
                context.user_data['editing_price'] = None
                await update.message.reply_text(
                    f"✅ Updated! <b>{CREDIT_PACKAGES[pkg_id]['credits']} Credits</b> now costs <b>${new_price:.2f}</b>\n\n"
                    f"Use /prices to see all packages.",
                    parse_mode='HTML'
                )
            else:
                context.user_data['editing_price'] = None
                await update.message.reply_text("❌ Package not found.")
        except ValueError:
            await update.message.reply_text("❌ Send a valid number (e.g. 25.00)")
        return
    
    # --- Handle admin price adding ---
    if context.user_data.get('adding_price') and user.id in ADMIN_TELEGRAM_IDS:
        step = context.user_data.get('adding_price_step')
        text = update.message.text.strip()
        
        if step == 'credits':
            try:
                credits = int(text)
                context.user_data['new_pkg_credits'] = credits
                context.user_data['adding_price_step'] = 'price'
                await update.message.reply_text(
                    f"✅ Credits: <b>{credits}</b>\n\n"
                    f"Step 2: Enter the price in USD (e.g. <code>25.00</code>):",
                    parse_mode='HTML'
                )
            except ValueError:
                await update.message.reply_text("❌ Send a whole number (e.g. 200)")
        
        elif step == 'price':
            try:
                price = float(text)
                credits = context.user_data.get('new_pkg_credits', 0)
                pkg_id = str(credits)
                CREDIT_PACKAGES[pkg_id] = {
                    "credits": credits,
                    "price": price,
                    "currency": "USDT"
                }
                context.user_data['adding_price'] = False
                context.user_data.pop('adding_price_step', None)
                context.user_data.pop('new_pkg_credits', None)
                await update.message.reply_text(
                    f"✅ Package added!\n\n"
                    f"📦 <b>{credits} Credits</b> — ${price:.2f} USDT\n\n"
                    f"Use /prices to see all packages.",
                    parse_mode='HTML'
                )
            except ValueError:
                await update.message.reply_text("❌ Send a valid price (e.g. 25.00)")
        return
    
    # --- Handle SIP trunk creation input ---
    if context.user_data.get('awaiting_trunk_input'):
        step = context.user_data.get('trunk_step', 'name')
        text = update.message.text.strip()
        
        if step == 'name':
            context.user_data['trunk_name'] = text
            context.user_data['trunk_step'] = 'host'
            await update.message.reply_text("🔌 <b>SIP Host</b>\n\nEnter the SIP server hostname/IP:\n\nExample: sip.provider.com", parse_mode='HTML')
        
        elif step == 'host':
            context.user_data['trunk_host'] = text
            context.user_data['trunk_step'] = 'username'
            await update.message.reply_text("🔌 <b>SIP Username</b>\n\nEnter SIP authentication username:", parse_mode='HTML')
        
        elif step == 'username':
            context.user_data['trunk_username'] = text
            context.user_data['trunk_step'] = 'password'
            await update.message.reply_text("🔌 <b>SIP Password</b>\n\nEnter SIP authentication password:", parse_mode='HTML')
        
        elif step == 'password':
            # All trunk info collected, create trunk
            user_data = await db.get_or_create_user(user.id)
            trunk = await db.create_trunk(
                user_id=user_data['id'],
                name=context.user_data.get('trunk_name', 'My Trunk'),
                sip_host=context.user_data.get('trunk_host', ''),
                sip_username=context.user_data.get('trunk_username', ''),
                sip_password=text,
            )
            
            # Clear state
            context.user_data['awaiting_trunk_input'] = False
            context.user_data.pop('trunk_step', None)
            context.user_data.pop('trunk_name', None)
            context.user_data.pop('trunk_host', None)
            context.user_data.pop('trunk_username', None)
            
            # Auto-reload PJSIP
            reload_status = ''
            try:
                result = subprocess.run(
                    ASTERISK_RELOAD_CMD, shell=True,
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    reload_status = '\n\n✅ PJSIP reloaded - trunk is active!'
                else:
                    reload_status = '\n\n⚠️ PJSIP reload failed - restart manually'
            except Exception:
                reload_status = '\n\n⚠️ Could not auto-reload Asterisk'
            
            await update.message.reply_text(
                f"✅ <b>Trunk Created!</b>\n\n"
                f"📛 Name: {trunk['name']}\n"
                f"🌐 Host: {trunk['sip_host']}\n"
                f"👤 User: {trunk['sip_username']}\n"
                f"🔗 Endpoint: <code>{trunk['pjsip_endpoint_name']}</code>"
                f"{reload_status}",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔌 My Trunks", callback_data="menu_trunks")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
                ])
            )
        return
    
    # --- Handle lead list name input ---
    if context.user_data.get('awaiting_lead_name'):
        user_data = await db.get_or_create_user(user.id)
        lead_name = update.message.text.strip()
        
        lead_id = await db.create_lead_list(
            user_id=user_data['id'],
            list_name=lead_name
        )
        
        context.user_data['awaiting_lead_name'] = False
        context.user_data['current_lead_id'] = lead_id
        context.user_data['awaiting_lead_file'] = True
        
        await update.message.reply_text(
            f"✅ <b>Lead List Created:</b> {lead_name}\n\n"
            f"📂 Now upload a CSV or TXT file with phone numbers (one per line).",
            parse_mode='HTML'
        )
        return
    
    # --- Handle campaign creation steps ---
    if not context.user_data.get('creating_campaign'):
        return
    
    step = context.user_data.get('campaign_step')
    
    if step == 'name':
        campaign_name = update.message.text.strip()
        user_data = await db.get_or_create_user(user.id)
        
        # Campaign will be created later when trunk + lead are selected
        context.user_data['campaign_name'] = campaign_name
        context.user_data['campaign_step'] = 'voice_choice'
        
        # Get saved voice files
        saved_voices = await db.get_user_voice_files(user_data['id'])
        
        keyboard = []
        if saved_voices:
            for voice in saved_voices[:5]:
                keyboard.append([InlineKeyboardButton(
                    f"🎤 {voice['name']} ({voice.get('duration', 0)}s)",
                    callback_data=f"voice_select_{voice['id']}"
                )])
        
        keyboard.append([InlineKeyboardButton("📤 Upload New Voice", callback_data="voice_upload_new")])
        
        await update.message.reply_text(
            f"✅ Name: <b>{campaign_name}</b>\n\n"
            f"Step 2: Select or Upload IVR Audio",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =============================================================================
# Voice/Audio Handler
# =============================================================================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice/audio file upload - saves to audio store"""
    user = update.effective_user
    
    if update.message.voice:
        file = update.message.voice
        duration = file.duration or 30
        ext = 'ogg'
    elif update.message.audio:
        file = update.message.audio
        duration = file.duration or 30
        ext = 'mp3'
    else:
        return
    
    user_data = await db.get_or_create_user(user.id)
    
    # Download and save to disk
    import os
    tg_file = await file.get_file()
    file_content = await tg_file.download_as_bytearray()
    
    voice_name = f"voice_{user_data['id']}_{int(datetime.now().timestamp())}"
    voice_dir = f"/opt/tgbot/voices/{user_data['id']}"
    os.makedirs(voice_dir, exist_ok=True)
    file_path = f"{voice_dir}/{voice_name}.{ext}"
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    voice_id = await db.save_voice_file(user_data['id'], voice_name, duration)
    
    # If in campaign creation, auto-select and advance
    in_campaign = (context.user_data.get('creating_campaign') and 
                   context.user_data.get('campaign_step') == 'voice_upload')
    
    if in_campaign:
        context.user_data['voice_id'] = voice_id
        context.user_data['campaign_step'] = 'select_trunk'
        
        trunks = await db.get_user_trunks(user_data['id'])
        keyboard = []
        if trunks:
            for trunk in trunks:
                status = "🟢" if trunk['status'] == 'active' else "🔴"
                keyboard.append([InlineKeyboardButton(
                    f"{status} {trunk['name']} ({trunk['sip_host']})",
                    callback_data=f"camp_trunk_{trunk['id']}"
                )])
        else:
            keyboard.append([InlineKeyboardButton("➕ Add SIP Trunk First", callback_data="trunk_add")])
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="menu_main")])
        
        await update.message.reply_text(
            f"✅ Voice Saved: {voice_name} ({duration}s)\n\n"
            f"Step 3: Select SIP Trunk\n\n"
            f"Choose which trunk to use for this campaign:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Standalone upload to audio store
        await update.message.reply_text(
            f"✅ <b>Audio Saved!</b>\n\n"
            f"🎵 Name: {voice_name}\n"
            f"⏱ Duration: {duration}s\n"
            f"📂 Path: <code>{file_path}</code>\n\n"
            f"You can select this voice when creating a campaign.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 My Voices", callback_data="menu_voices")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# File Upload Handler (CSV/TXT for leads)
# =============================================================================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CSV/TXT file upload for leads or direct campaign upload"""
    user = update.effective_user
    
    filename = update.message.document.file_name.lower()
    
    # Handle WAV/MP3 audio files for voice store
    if filename.endswith('.wav') or filename.endswith('.mp3') or filename.endswith('.ogg'):
        file = await update.message.document.get_file()
        file_content = await file.download_as_bytearray()
        
        user_data = await db.get_or_create_user(user.id)
        voice_name = filename.rsplit('.', 1)[0]  # Use filename without extension
        
        # Save to server path
        import os
        voice_dir = f"/opt/tgbot/voices/{user_data['id']}"
        os.makedirs(voice_dir, exist_ok=True)
        file_path = f"{voice_dir}/{filename}"
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        voice_id = await db.save_voice_file(user_data['id'], voice_name, 0)
        
        # If in campaign creation voice step, auto-select it
        if context.user_data.get('creating_campaign') and context.user_data.get('campaign_step') == 'voice_upload':
            context.user_data['voice_id'] = voice_id
            context.user_data['campaign_step'] = 'select_trunk'
            
            trunks = await db.get_user_trunks(user_data['id'])
            keyboard = []
            if trunks:
                for trunk in trunks:
                    status = "🟢" if trunk['status'] == 'active' else "🔴"
                    keyboard.append([InlineKeyboardButton(
                        f"{status} {trunk['name']} ({trunk['sip_host']})",
                        callback_data=f"camp_trunk_{trunk['id']}"
                    )])
            else:
                keyboard.append([InlineKeyboardButton("➕ Add SIP Trunk First", callback_data="trunk_add")])
            keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="menu_main")])
            
            await update.message.reply_text(
                f"✅ Voice Saved: <b>{voice_name}</b>\n\n"
                f"Step 3: Select SIP Trunk:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Audio Saved!</b>\n\n"
                f"🎵 Name: {voice_name}\n"
                f"📂 Path: <code>{file_path}</code>\n\n"
                f"You can select this voice when creating a campaign.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎵 My Voices", callback_data="menu_voices")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
                ])
            )
        return
    
    if not (filename.endswith('.csv') or filename.endswith('.txt')):
        await update.message.reply_text("❌ Supported files: CSV, TXT (numbers) or WAV, MP3, OGG (audio)")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    
    try:
        text_content = file_content.decode('utf-8')
        phone_numbers = []
        
        if filename.endswith('.csv'):
            reader = csv.reader(io.StringIO(text_content))
            for row in reader:
                if row and row[0].strip():
                    phone = ''.join(filter(str.isdigit, row[0]))
                    if phone:
                        phone_numbers.append(phone)
        else:
            for line in text_content.strip().split('\n'):
                line = line.strip()
                if line:
                    phone = ''.join(filter(str.isdigit, line))
                    if phone:
                        phone_numbers.append(phone)
        
        if not phone_numbers:
            await update.message.reply_text("❌ No valid phone numbers found")
            return
        
        # Check if uploading to a lead list
        if context.user_data.get('awaiting_lead_file'):
            lead_id = context.user_data.get('current_lead_id')
            if lead_id:
                count = await db.add_lead_numbers(lead_id, phone_numbers)
                context.user_data['awaiting_lead_file'] = False
                context.user_data.pop('current_lead_id', None)
                
                await update.message.reply_text(
                    f"✅ <b>{count} numbers added to lead list!</b>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 My Leads", callback_data="menu_leads")],
                        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
                    ])
                )
            return
        
        # Check if uploading directly for a campaign (legacy path)
        if context.user_data.get('creating_campaign') and context.user_data.get('campaign_step') == 'upload':
            campaign_id = context.user_data.get('campaign_id')
            if campaign_id:
                count = await db.add_campaign_numbers(campaign_id, phone_numbers)
                context.user_data['creating_campaign'] = False
                
                await update.message.reply_text(
                    f"✅ <b>Campaign Ready!</b>\n\n"
                    f"📊 Numbers: {count}\n"
                    f"💰 Est. cost: ~${count * 1.0:.2f}",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🚀 Start Campaign", callback_data=f"start_campaign_{campaign_id}")
                    ]])
                )
            return
        
        # Default: ask to create a lead list
        await update.message.reply_text(
            f"📂 Found {len(phone_numbers)} numbers.\n\nUse <b>📋 My Leads</b> to create a lead list first, then upload.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 My Leads", callback_data="menu_leads")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"File processing error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


# =============================================================================
# Start Campaign Callback
# =============================================================================

async def handle_start_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start campaign callback"""
    query = update.callback_query
    await query.answer()
    
    campaign_id = int(query.data.split('_')[2])
    await db.start_campaign(campaign_id)
    
    await query.edit_message_text(
        f"🚀 <b>Campaign #{campaign_id} Started!</b>\n\n"
        f"• Phone numbers are being dialed automatically\n"
        f"• IVR plays when answered\n"
        f"• DTMF detection tracks Press-1\n"
        f"• Credits deducted per call\n\n"
        f"Use /campaigns to check progress.",
        parse_mode='HTML'
    )


# =============================================================================
# Voice Selection Callbacks
# =============================================================================

async def handle_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice file selection/upload callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "voice_upload_new":
        context.user_data['campaign_step'] = 'voice_upload'
        await query.edit_message_text(
            "📤 <b>Upload Voice File</b>\n\n"
            "Send a voice message or audio file for your IVR.\n"
            "Supported: voice messages, .mp3, .wav, .ogg",
            parse_mode='HTML'
        )
    
    elif data.startswith("voice_select_"):
        voice_id = int(data.replace("voice_select_", ""))
        context.user_data['voice_id'] = voice_id
        context.user_data['campaign_step'] = 'select_trunk'
        
        # Show trunk selection
        user_data = await db.get_or_create_user(user.id)
        trunks = await db.get_user_trunks(user_data['id'])
        
        keyboard = []
        if trunks:
            for trunk in trunks:
                status = "🟢" if trunk['status'] == 'active' else "🔴"
                keyboard.append([InlineKeyboardButton(
                    f"{status} {trunk['name']} ({trunk['sip_host']})",
                    callback_data=f"camp_trunk_{trunk['id']}"
                )])
        else:
            keyboard.append([InlineKeyboardButton("➕ Add SIP Trunk First", callback_data="trunk_add")])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="menu_main")])
        
        await query.edit_message_text(
            "✅ Voice selected!\n\n"
            "Step 3: <b>Select SIP Trunk</b>\n\n"
            "Choose which trunk to route calls through:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("voice_delete_"):
        voice_id = int(data.replace("voice_delete_", ""))
        user_data = await db.get_or_create_user(user.id)
        
        # Delete from DB
        try:
            if hasattr(db, 'pool'):
                async with db.pool.acquire() as conn:
                    await conn.execute("DELETE FROM voice_files WHERE id = $1 AND user_id = $2", voice_id, user_data['id'])
            elif hasattr(db, 'voice_files'):
                db.voice_files.pop(voice_id, None)
        except Exception:
            pass
        
        await query.edit_message_text(
            "🗑️ Voice deleted!\n\nUse 🎵 My Voices to see remaining files.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 My Voices", callback_data="menu_voices")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# Campaign Setup Callbacks (trunk + lead selection)
# =============================================================================

async def handle_campaign_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trunk and lead selection during campaign creation"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    user_data = await db.get_or_create_user(user.id)
    
    if data.startswith("camp_trunk_"):
        # User selected a trunk for campaign
        trunk_id = int(data.replace("camp_trunk_", ""))
        context.user_data['campaign_trunk_id'] = trunk_id
        context.user_data['campaign_step'] = 'select_lead'
        
        trunk = await db.get_trunk(trunk_id)
        
        # Show lead list selection
        leads = await db.get_user_leads(user_data['id'])
        
        keyboard = []
        if leads:
            for lead in leads:
                avail = lead.get('available_numbers', 0)
                total = lead.get('total_numbers', 0)
                keyboard.append([InlineKeyboardButton(
                    f"📋 {lead['list_name']} ({avail}/{total} avail)",
                    callback_data=f"camp_lead_{lead['id']}"
                )])
        else:
            keyboard.append([InlineKeyboardButton("➕ Create Lead List First", callback_data="lead_add")])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="menu_main")])
        
        await query.edit_message_text(
            f"✅ Trunk: <b>{trunk['name'] if trunk else 'Selected'}</b>\n\n"
            f"Step 4: <b>Select Lead List</b>\n\n"
            f"Choose which phone numbers to call:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("camp_lead_"):
        # User selected a lead list - show country code selection
        lead_id = int(data.replace("camp_lead_", ""))
        context.user_data['campaign_lead_id'] = lead_id
        context.user_data['campaign_step'] = 'select_country'
        
        keyboard = []
        for code, label in SUPPORTED_COUNTRY_CODES.items():
            keyboard.append([InlineKeyboardButton(
                f"{label}" + (f" (+{code})" if code != 'none' else ""),
                callback_data=f"camp_cc_{code}"
            )])
        
        await query.edit_message_text(
            "🌍 Step 5: <b>Select Country Code</b>\n\n"
            "Choose the country for your phone numbers:\n"
            "This prefix will be added to all numbers.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("camp_cc_"):
        # User selected country code - show CPS selection
        country_code = data.replace("camp_cc_", "")
        if country_code == 'none':
            country_code = ''
        
        context.user_data['campaign_country_code'] = country_code
        context.user_data['campaign_step'] = 'select_cps'
        
        keyboard = [
            [
                InlineKeyboardButton("1 Call", callback_data="camp_cps_1"),
                InlineKeyboardButton("3 Calls", callback_data="camp_cps_3"),
                InlineKeyboardButton("5 Calls", callback_data="camp_cps_5"),
            ],
            [
                InlineKeyboardButton("10 Calls", callback_data="camp_cps_10"),
                InlineKeyboardButton("20 Calls", callback_data="camp_cps_20"),
                InlineKeyboardButton("30 Calls", callback_data="camp_cps_30"),
            ],
            [
                InlineKeyboardButton("40 Calls", callback_data="camp_cps_40"),
                InlineKeyboardButton("50 Calls", callback_data="camp_cps_50"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(
            "📞 Step 6: <b>Concurrent Calls (CPS)</b>\n\n"
            "How many calls should run at the same time?\n\n"
            "⚡ Higher = Faster but more trunk load\n"
            "🐢 Lower = Slower but more stable",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("camp_cps_"):
        # User selected CPS - CREATE the campaign now
        cps = int(data.replace("camp_cps_", ""))
        
        trunk_id = context.user_data.get('campaign_trunk_id')
        lead_id = context.user_data.get('campaign_lead_id')
        campaign_name = context.user_data.get('campaign_name', 'Unnamed Campaign')
        country_code = context.user_data.get('campaign_country_code', '')
        
        lead = await db.get_lead(lead_id)
        trunk = await db.get_trunk(trunk_id) if trunk_id else None
        
        campaign_id = await db.create_campaign(
            user_id=user_data['id'],
            name=campaign_name,
            trunk_id=trunk_id,
            lead_id=lead_id,
            caller_id=user_data.get('caller_id'),
            country_code=country_code,
            cps=cps
        )
        
        # Store campaign settings
        context.user_data['campaign_id'] = campaign_id
        context.user_data['campaign_cps'] = cps
        context.user_data['creating_campaign'] = False
        
        avail = lead.get('available_numbers', 0) if lead else 0
        trunk_name = trunk.get('name', 'N/A') if trunk else 'N/A'
        lead_name = lead.get('list_name', 'N/A') if lead else 'N/A'
        cc_display = f'+{country_code}' if country_code else 'No prefix'
        
        await query.edit_message_text(
            f"✅ <b>Campaign Ready!</b>\n\n"
            f"📛 Name: {campaign_name}\n"
            f"🔌 Trunk: {trunk_name}\n"
            f"📋 Leads: {lead_name} ({avail} numbers)\n"
            f"🌍 Country: {cc_display}\n"
            f"📞 CPS: {cps} concurrent calls\n\n"
            f"Click START to begin calling!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Campaign", callback_data=f"start_campaign_{campaign_id}")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# Menu Navigation Callbacks
# =============================================================================

async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu navigation callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("menu_", "")
    user = update.effective_user
    user_data = await db.get_or_create_user(user.id)
    
    if action == "main":
        stats = await db.get_user_stats(user.id)
        dashboard_text = f"""
<b>1337 Press One</b>

Hello {user.first_name or 'User'}, welcome to the advanced press-one system.

<b>Your Settings</b>
Country Code: {user_data.get('country_code', '+1')} | Caller ID: {user_data.get('caller_id', 'Not Set')}

<b>Account & System Info</b>
Balance: ${user_data.get('credits', 0):.2f} | Trunks: {stats.get('trunk_count', 0)} | Leads: {stats.get('lead_count', 0)}
Campaigns: {stats.get('campaign_count', 0)} | Total Calls: {user_data.get('total_calls', 0)}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch"),
                InlineKeyboardButton("💰 Check Balance", callback_data="menu_balance")
            ],
            [
                InlineKeyboardButton("🔌 My Trunks", callback_data="menu_trunks"),
                InlineKeyboardButton("📋 My Leads", callback_data="menu_leads")
            ],
            [
                InlineKeyboardButton("🔧 Configure CID", callback_data="menu_configure_cid"),
                InlineKeyboardButton("📊 Live Statistics", callback_data="menu_statistics")
            ],
            [
                InlineKeyboardButton("🛠️ Tools & Utilities", callback_data="menu_tools"),
                InlineKeyboardButton("🎵 My Voices", callback_data="menu_voices")
            ],
            [
                InlineKeyboardButton("🔑 Account Info", callback_data="menu_account"),
                InlineKeyboardButton("💬 Support", callback_data="menu_support")
            ]
        ]
        
        # Add admin panel button for admins
        if user.id in ADMIN_TELEGRAM_IDS:
            keyboard.append([
                InlineKeyboardButton("🛡️ Admin Panel", callback_data="menu_admin")
            ])
        
        await query.edit_message_text(dashboard_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "admin":
        if user.id not in ADMIN_TELEGRAM_IDS:
            await query.edit_message_text("❌ Admin only.")
            return
        
        all_users = await db.get_all_users()
        user_count = len(all_users) if all_users else 0
        
        admin_text = (
            "🛡️ <b>Admin Panel</b>\n\n"
            f"👥 Total Users: <b>{user_count}</b>\n"
            f"📦 Credit Packages: <b>{len(CREDIT_PACKAGES)}</b>\n\n"
            "Select an option:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("👥 View Users", callback_data="menu_admin_users"),
                InlineKeyboardButton("💰 Manage Prices", callback_data="menu_admin_prices")
            ],
            [
                InlineKeyboardButton("📊 System Stats", callback_data="menu_admin_stats")
            ],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(admin_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "admin_users":
        if user.id not in ADMIN_TELEGRAM_IDS:
            return
        
        all_users = await db.get_all_users()
        if not all_users:
            await query.edit_message_text(
                "📭 No registered users yet.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_admin")]])
            )
            return
        
        text = f"👥 <b>Registered Users ({len(all_users)})</b>\n\n"
        for i, u in enumerate(all_users, 1):
            username = u.get('username', 'N/A') or 'N/A'
            name = u.get('first_name', '') or ''
            credits = u.get('credits', 0)
            calls = u.get('total_calls', 0)
            created = u.get('created_at')
            last_active = u.get('last_active')
            status = '🟢' if u.get('is_active', True) else '🔴'
            tg_id = u.get('telegram_id', 'N/A')
            
            created_str = created.strftime('%d/%m/%Y %H:%M') if created else 'N/A'
            active_str = last_active.strftime('%d/%m/%Y %H:%M') if last_active else 'N/A'
            
            text += (
                f"{status} <b>{i}. {name}</b> (@{username})\n"
                f"   🆔 <code>{tg_id}</code>\n"
                f"   💰 ${credits:.2f} | 📞 {calls} calls\n"
                f"   📅 {created_str} | 🕐 {active_str}\n\n"
            )
            if len(text) > 3500:
                text += f"... +{len(all_users) - i} more"
                break
        
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="menu_admin_users")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="menu_admin")]
            ])
        )
    
    elif action == "admin_prices":
        if user.id not in ADMIN_TELEGRAM_IDS:
            return
        
        text = "💰 <b>Credit Packages</b>\n\n"
        keyboard = []
        for pkg_id, pkg in CREDIT_PACKAGES.items():
            text += f"📦 <b>{pkg['credits']} Credits</b> — ${pkg['price']:.2f} {pkg['currency']}\n"
            keyboard.append([
                InlineKeyboardButton(f"✏️ Edit {pkg['credits']}cr", callback_data=f"price_edit_{pkg_id}"),
                InlineKeyboardButton(f"🗑️ Delete", callback_data=f"price_del_{pkg_id}")
            ])
        keyboard.append([InlineKeyboardButton("➕ Add Package", callback_data="price_add")])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="menu_admin")])
        text += "\nTap edit to change price."
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "admin_stats":
        if user.id not in ADMIN_TELEGRAM_IDS:
            return
        
        all_users = await db.get_all_users()
        total_users = len(all_users) if all_users else 0
        total_credits = sum(u.get('credits', 0) for u in all_users) if all_users else 0
        total_spent = sum(u.get('total_spent', 0) for u in all_users) if all_users else 0
        total_calls = sum(u.get('total_calls', 0) for u in all_users) if all_users else 0
        
        text = (
            "📊 <b>System Statistics</b>\n\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"💰 Total Credits in System: <b>${total_credits:.2f}</b>\n"
            f"💵 Total Revenue: <b>${total_spent:.2f}</b>\n"
            f"📞 Total Calls Made: <b>{total_calls}</b>\n"
            f"📦 Credit Packages: <b>{len(CREDIT_PACKAGES)}</b>\n"
        )
        
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="menu_admin_stats")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="menu_admin")]
            ])
        )
    
    elif action == "voices":
        user_data_full = await db.get_or_create_user(user.id)
        voices = await db.get_user_voice_files(user_data_full['id'])
        
        text = "🎵 <b>My Voice Files</b>\n\n"
        keyboard = []
        
        if voices:
            for v in voices:
                dur = v.get('duration', 0)
                name = v.get('name', 'Unnamed')
                text += f"🎶 <b>{name}</b> ({dur}s)\n"
                keyboard.append([
                    InlineKeyboardButton(f"🗑️ Delete {name}", callback_data=f"voice_delete_{v['id']}")
                ])
        else:
            text += "📭 No voice files yet.\n"
        
        text += (
            "\n<b>How to upload:</b>\n"
            "🎤 Send a voice message\n"
            "📂 Upload a WAV, MP3, or OGG file\n\n"
            "Files will be saved to your audio store."
        )
        
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
        
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif action == "launch":
        balance = user_data.get('credits', user_data.get('balance', 0))
        if balance <= 0 and not TEST_MODE:
            await query.edit_message_text(
                "❌ Insufficient credits.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Add Credits", callback_data="menu_balance")],
                    [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
                ])
            )
            return
        
        context.user_data['creating_campaign'] = True
        context.user_data['campaign_step'] = 'name'
        
        await query.edit_message_text(
            "🚀 <b>Create New Campaign</b>\n\n"
            "<b>Campaign Setup Flow:</b>\n"
            "1️⃣ Campaign Name\n"
            "2️⃣ Voice File (upload or select)\n"
            "3️⃣ Select SIP Trunk\n"
            "4️⃣ Select Lead List\n"
            "5️⃣ Country Code\n"
            "6️⃣ Concurrent Calls (CPS)\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📝 <b>Step 1:</b> Enter campaign name:",
            parse_mode='HTML'
        )
    
    elif action == "balance":
        stats = await db.get_user_stats(user.id)
        credits = stats.get('credits', 0) if stats else 0
        
        if credits > 100: credit_status = "🟢 Excellent"
        elif credits > 50: credit_status = "🟡 Good"
        elif credits > 10: credit_status = "🟠 Low"
        else: credit_status = "🔴 Critical"
        
        balance_text = f"""
💰 <b>Account Balance</b>

<b>Status:</b> {credit_status}
<b>Credits:</b> {credits:.2f}

<b>Stats:</b>
💵 Spent: ${stats.get('total_spent', 0):.2f}
📞 Calls: {stats.get('total_calls', 0)}
📊 Campaigns: {stats.get('campaign_count', 0)}
🔌 Trunks: {stats.get('trunk_count', 0)}
📋 Leads: {stats.get('lead_count', 0)}
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Buy Credits", callback_data="menu_buy")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(balance_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "buy":
        buy_text = "💳 <b>Purchase Credits</b>\n\n"
        keyboard = []
        
        for package_id, pkg in CREDIT_PACKAGES.items():
            buy_text += f"📦 {pkg['credits']} Credits — ${pkg['price']} {pkg['currency']}\n"
            keyboard.append([InlineKeyboardButton(
                f"Select {pkg['credits']} Credits",
                callback_data=f"buy_{package_id}"
            )])
        
        buy_text += "\n✅ Secure payments via Oxapay\n✅ Instant delivery"
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        
        await query.edit_message_text(buy_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "trunks":
        # SIP Trunk Management
        trunks = await db.get_user_trunks(user_data['id'])
        
        trunks_text = "🔌 <b>My SIP Trunks</b>\n\n"
        
        if trunks:
            for trunk in trunks:
                status = "🟢" if trunk['status'] == 'active' else "🔴"
                trunks_text += (
                    f"{status} <b>{trunk['name']}</b>\n"
                    f"   🌐 {trunk['sip_host']}:{trunk.get('sip_port', 5060)}\n"
                    f"   👤 {trunk['sip_username']}\n"
                    f"   🔗 <code>{trunk['pjsip_endpoint_name']}</code>\n\n"
                )
        else:
            trunks_text += "No trunks configured yet.\n\nAdd your first SIP trunk to start making calls!\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add New Trunk", callback_data="trunk_add")],
        ]
        
        if trunks:
            for trunk in trunks:
                keyboard.append([
                    InlineKeyboardButton(f"🗑 Delete {trunk['name'][:20]}", callback_data=f"trunk_delete_{trunk['id']}")
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
        
        await query.edit_message_text(trunks_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "leads":
        # Lead List Management
        leads = await db.get_user_leads(user_data['id'])
        
        leads_text = "📋 <b>My Lead Lists</b>\n\n"
        
        if leads:
            for lead in leads:
                avail = lead.get('available_numbers', 0)
                total = lead.get('total_numbers', 0)
                leads_text += (
                    f"📋 <b>{lead['list_name']}</b>\n"
                    f"   📊 {avail}/{total} available | Created: {lead['created_at'].strftime('%Y-%m-%d') if hasattr(lead['created_at'], 'strftime') else 'N/A'}\n\n"
                )
        else:
            leads_text += "No lead lists yet.\n\nCreate a lead list and upload phone numbers!\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Create Lead List", callback_data="lead_add")],
        ]
        
        if leads:
            for lead in leads:
                keyboard.append([
                    InlineKeyboardButton(f"🗑 Delete {lead['list_name'][:20]}", callback_data=f"lead_delete_{lead['id']}")
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
        
        await query.edit_message_text(leads_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "configure_cid":
        current_cid = user_data.get('caller_id', 'Not Set')
        
        cid_text = f"""
🔧 <b>Caller ID Management</b>

<b>Current CID:</b> {current_cid}

<b>Options:</b>
• Preset CIDs - Verified, high-performance numbers
• Custom CID - Use your own number
"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Preset CIDs", callback_data="cid_preset")],
            [InlineKeyboardButton("✏️ Custom CID", callback_data="cid_custom")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(cid_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "statistics":
        campaigns = await db.get_user_campaigns(user_data['id'], limit=5)
        
        stats_text = f"""
📊 <b>Live Statistics</b>

<b>Overview</b>
Total Campaigns: {len(campaigns)}
Total Calls: {user_data.get('total_calls', 0)}

<b>Recent Campaigns</b>
"""
        
        if campaigns:
            for camp in campaigns[:3]:
                stats_text += f"\n• {camp.get('name', 'Unnamed')} - {camp.get('status', 'Unknown')}"
        else:
            stats_text += "\nNo campaigns yet"
        
        keyboard = [
            [InlineKeyboardButton("📊 View All Campaigns", callback_data="menu_campaigns")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(stats_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "campaigns":
        campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
        
        if not campaigns:
            await query.edit_message_text(
                "📂 <b>No Campaigns</b>\n\nCreate your first campaign!",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
                ])
            )
            return
        
        text = f"📊 <b>My Campaigns</b> ({len(campaigns)})\n\n"
        keyboard = []
        for camp in campaigns:
            emoji = {'running': '🟢', 'paused': '🟡', 'completed': '✅', 'failed': '❌'}.get(camp.get('status', ''), '⚪')
            trunk = camp.get('trunk_name', '-')
            text += f"{emoji} <b>{camp['name']}</b>\n   📞 {camp.get('completed', 0)}/{camp.get('total_numbers', 0)} | 🔌 {trunk}\n\n"
            
            cid = camp['id']
            if camp.get('status') == 'running':
                keyboard.append([
                    InlineKeyboardButton(f"⏸️ Pause", callback_data=f"pause_{cid}"),
                    InlineKeyboardButton(f"📊 Details", callback_data=f"details_{cid}")
                ])
            elif camp.get('status') == 'paused':
                keyboard.append([
                    InlineKeyboardButton(f"▶️ Resume", callback_data=f"resume_{cid}"),
                    InlineKeyboardButton(f"📊 Details", callback_data=f"details_{cid}")
                ])
            else:
                keyboard.append([InlineKeyboardButton(f"📊 {camp['name'][:25]}", callback_data=f"details_{cid}")])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="menu_campaigns"),
            InlineKeyboardButton("🔙 Menu", callback_data="menu_main")
        ])
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "tools":
        await query.edit_message_text(
            "🛠️ <b>Tools & Utilities</b>\n\n• CSV Validator\n• Number Formatter\n• DNC Checker\n\nMore tools coming soon!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]])
        )
    
    elif action == "account":
        stats = await db.get_user_stats(user.id)
        account_text = f"""
🔑 <b>Account Information</b>

<b>Profile</b>
Username: @{user.username or 'Not set'}
User ID: {user.id}

<b>Settings</b>
Caller ID: {user_data.get('caller_id', 'Not Set')}
Balance: ${user_data.get('credits', 0):.2f}

<b>Resources</b>
🔌 SIP Trunks: {stats.get('trunk_count', 0)}
📋 Lead Lists: {stats.get('lead_count', 0)}
📊 Campaigns: {stats.get('campaign_count', 0)}
📞 Total Calls: {stats.get('total_calls', 0)}
"""
        
        await query.edit_message_text(
            account_text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]])
        )
    
    elif action == "support":
        await query.edit_message_text(
            "💬 <b>Contact Support</b>\n\n📧 Email: support@1337.com\n💬 Telegram: @1337Support\n\nResponse time: 2-4 hours",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]])
        )


# =============================================================================
# Trunk Management Callbacks
# =============================================================================

async def handle_trunk_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SIP trunk add/delete callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "trunk_add":
        # Start trunk creation flow
        context.user_data['awaiting_trunk_input'] = True
        context.user_data['trunk_step'] = 'name'
        
        await query.edit_message_text(
            "🔌 <b>Add New SIP Trunk</b>\n\n"
            "Step 1: Enter a name for this trunk\n\n"
            "Example: MagnusBilling Main",
            parse_mode='HTML'
        )
    
    elif data.startswith("trunk_delete_"):
        trunk_id = int(data.replace("trunk_delete_", ""))
        trunk = await db.get_trunk(trunk_id)
        
        await query.edit_message_text(
            f"⚠️ <b>Delete Trunk?</b>\n\n"
            f"Trunk: {trunk['name'] if trunk else 'Unknown'}\n\n"
            f"This action cannot be undone.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"trunk_confirm_delete_{trunk_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="menu_trunks")]
            ])
        )
    
    elif data.startswith("trunk_confirm_delete_"):
        trunk_id = int(data.replace("trunk_confirm_delete_", ""))
        await db.delete_trunk(trunk_id)
        
        await query.edit_message_text(
            "✅ Trunk deleted.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔌 My Trunks", callback_data="menu_trunks")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# Lead Management Callbacks
# =============================================================================

async def handle_lead_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lead list add/delete callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "lead_add":
        context.user_data['awaiting_lead_name'] = True
        
        await query.edit_message_text(
            "📋 <b>Create Lead List</b>\n\n"
            "Enter a name for your lead list:\n\n"
            "Example: US Contacts Feb 2026",
            parse_mode='HTML'
        )
    
    elif data.startswith("lead_delete_"):
        lead_id = int(data.replace("lead_delete_", ""))
        lead = await db.get_lead(lead_id)
        
        await query.edit_message_text(
            f"⚠️ <b>Delete Lead List?</b>\n\n"
            f"List: {lead['list_name'] if lead else 'Unknown'}\n\n"
            f"All phone numbers in this list will be deleted.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"lead_confirm_delete_{lead_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="menu_leads")]
            ])
        )
    
    elif data.startswith("lead_confirm_delete_"):
        lead_id = int(data.replace("lead_confirm_delete_", ""))
        await db.delete_lead_list(lead_id)
        
        await query.edit_message_text(
            "✅ Lead list deleted.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 My Leads", callback_data="menu_leads")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# Caller ID Callbacks
# =============================================================================

async def handle_cid_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Caller ID configuration callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "cid_preset":
        cids = await db.get_preset_cids()
        keyboard = []
        for cid in cids:
            keyboard.append([InlineKeyboardButton(
                f"📞 {cid.get('name', 'CID')} — {cid['number']}",
                callback_data=f"setcid_{cid['number']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_configure_cid")])
        
        await query.edit_message_text(
            "📋 <b>Select Preset CID</b>\n\nChoose a verified caller ID:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "cid_custom":
        context.user_data['awaiting_custom_cid'] = True
        
        await query.edit_message_text(
            "✏️ <b>Enter Custom CID</b>\n\nType your phone number (10-15 digits):\n\nExample: 12025551234",
            parse_mode='HTML'
        )
    
    elif data.startswith("setcid_"):
        cid = data.replace("setcid_", "")
        await db.set_caller_id(user.id, cid)
        
        await query.edit_message_text(
            f"✅ <b>CID Set:</b> {cid}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )


# =============================================================================
# Campaign Control Callbacks (pause/resume/details/logs)
# =============================================================================

async def handle_campaign_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle campaign pause/resume/details/logs callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("pause_"):
        campaign_id = int(data.replace("pause_", ""))
        await db.stop_campaign(campaign_id)
        
        await query.edit_message_text(
            f"⏸️ <b>Campaign #{campaign_id} Paused</b>\n\nUse /campaigns to resume.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Campaigns", callback_data="menu_campaigns")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )
    
    elif data.startswith("resume_"):
        campaign_id = int(data.replace("resume_", ""))
        await db.start_campaign(campaign_id)
        
        await query.edit_message_text(
            f"▶️ <b>Campaign #{campaign_id} Resumed</b>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Campaigns", callback_data="menu_campaigns")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )
    
    elif data.startswith("details_"):
        campaign_id = int(data.replace("details_", ""))
        stats = await db.get_campaign_stats(campaign_id)
        
        if not stats:
            await query.edit_message_text("❌ Campaign not found.")
            return
        
        total = stats.get('total_numbers', 0)
        completed = stats.get('completed', 0)
        answered = stats.get('answered', 0)
        pressed = stats.get('pressed_one', 0)
        failed = stats.get('failed', 0)
        cost = stats.get('actual_cost', 0)
        progress = (completed / total * 100) if total > 0 else 0
        answer_rate = (answered / completed * 100) if completed > 0 else 0
        press_rate = (pressed / answered * 100) if answered > 0 else 0
        
        trunk_name = stats.get('trunk_name', 'N/A')
        lead_name = stats.get('lead_name', 'N/A')
        
        details_text = f"""
📊 <b>{stats.get('name', 'Campaign')}</b>

<b>Status:</b> {stats.get('status', 'Unknown').upper()}
<b>Trunk:</b> 🔌 {trunk_name}
<b>Leads:</b> 📋 {lead_name}

<b>Progress:</b> {completed}/{total} ({progress:.0f}%)
<b>Answered:</b> {answered} ({answer_rate:.0f}%)
<b>Press-1:</b> {pressed} ({press_rate:.0f}%)
<b>Failed:</b> {failed}
<b>Cost:</b> ${cost:.2f}
"""
        
        keyboard = [
            [InlineKeyboardButton("📝 Call Logs", callback_data=f"logs_{campaign_id}")],
        ]
        
        status = stats.get('status', '')
        if status == 'running':
            keyboard.append([InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{campaign_id}")])
        elif status == 'paused':
            keyboard.append([InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{campaign_id}")])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data=f"details_{campaign_id}"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_campaigns")
        ])
        
        await query.edit_message_text(details_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("logs_"):
        campaign_id = int(data.replace("logs_", ""))
        logs = await db.get_campaign_call_logs(campaign_id, limit=10)
        
        if not logs:
            await query.edit_message_text(
                "📝 <b>No Logs Yet</b>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"details_{campaign_id}")]
                ])
            )
            return
        
        text = f"📝 <b>Call Logs</b> (Last {len(logs)})\n\n"
        for log in logs[:10]:
            emoji = "✅" if log.get('pressed_one') else ("📞" if log.get('answered') else "❌")
            text += f"{emoji} {log.get('phone_number', 'N/A')} | {log.get('duration', 0)}s | ${log.get('cost', 0):.2f}\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"details_{campaign_id}")]
            ])
        )


# =============================================================================
# Main Application
# =============================================================================

async def post_init(application: Application):
    """Initialize database after app is created"""
    await db.connect()
    logger.info("✅ Bot initialized")


async def post_shutdown(application: Application):
    """Cleanup on shutdown"""
    await db.close()
    logger.info("🛑 Bot stopped")


# =============================================================================
# Admin Commands
# =============================================================================

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /users command - Admin only: list all registered users"""
    user = update.effective_user
    if user.id not in ADMIN_TELEGRAM_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    all_users = await db.get_all_users()
    
    if not all_users:
        await update.message.reply_text("📭 No registered users yet.")
        return
    
    text = f"👥 <b>Registered Users ({len(all_users)})</b>\n\n"
    
    for i, u in enumerate(all_users, 1):
        username = u.get('username', 'N/A') or 'N/A'
        name = u.get('first_name', '') or ''
        credits = u.get('credits', 0)
        calls = u.get('total_calls', 0)
        created = u.get('created_at')
        last_active = u.get('last_active')
        status = '🟢' if u.get('is_active', True) else '🔴'
        tg_id = u.get('telegram_id', 'N/A')
        
        created_str = created.strftime('%d/%m/%Y %H:%M') if created else 'N/A'
        active_str = last_active.strftime('%d/%m/%Y %H:%M') if last_active else 'N/A'
        
        text += (
            f"{status} <b>{i}. {name}</b> (@{username})\n"
            f"   🆔 <code>{tg_id}</code>\n"
            f"   💰 ${credits:.2f} | 📞 {calls} calls\n"
            f"   📅 Registered: {created_str}\n"
            f"   🕐 Last active: {active_str}\n\n"
        )
        
        # Telegram message limit - split if too long
        if len(text) > 3500:
            text += f"... and {len(all_users) - i} more users"
            break
    
    await update.message.reply_text(text, parse_mode='HTML')

async def admin_prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /prices command - Admin only"""
    user = update.effective_user
    if user.id not in ADMIN_TELEGRAM_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    text = "💰 <b>Credit Packages</b>\n\n"
    keyboard = []
    
    for pkg_id, pkg in CREDIT_PACKAGES.items():
        text += f"📦 <b>{pkg['credits']} Credits</b> — ${pkg['price']:.2f} {pkg['currency']}\n"
        keyboard.append([
            InlineKeyboardButton(f"✏️ Edit {pkg['credits']}cr", callback_data=f"price_edit_{pkg_id}"),
            InlineKeyboardButton(f"🗑️ Delete", callback_data=f"price_del_{pkg_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add New Package", callback_data="price_add")])
    
    text += "\nTap edit to change a package price."
    
    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_admin_price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin price management callbacks"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    if user.id not in ADMIN_TELEGRAM_IDS:
        await query.edit_message_text("❌ Admin only.")
        return
    
    data = query.data
    
    if data.startswith("price_edit_"):
        pkg_id = data.replace("price_edit_", "")
        if pkg_id in CREDIT_PACKAGES:
            pkg = CREDIT_PACKAGES[pkg_id]
            context.user_data['editing_price'] = pkg_id
            await query.edit_message_text(
                f"✏️ <b>Edit Package: {pkg['credits']} Credits</b>\n\n"
                f"Current price: ${pkg['price']:.2f}\n\n"
                f"Send the new price (number only, e.g. <code>25.00</code>):",
                parse_mode='HTML'
            )
    
    elif data.startswith("price_del_"):
        pkg_id = data.replace("price_del_", "")
        if pkg_id in CREDIT_PACKAGES:
            del CREDIT_PACKAGES[pkg_id]
            await query.edit_message_text(
                f"🗑️ Package deleted!\n\nUse /prices to see updated list."
            )
    
    elif data == "price_add":
        context.user_data['adding_price'] = True
        context.user_data['adding_price_step'] = 'credits'
        await query.edit_message_text(
            "➕ <b>Add New Package</b>\n\n"
            "Step 1: How many credits?\n"
            "Send a number (e.g. <code>200</code>):",
            parse_mode='HTML'
        )

# =============================================================================
# Bot Lifecycle Hooks
# =============================================================================

async def post_init(application):
    """Called after bot initialization - connect to database"""
    await db.connect()
    logger.info("✅ Database connected")

async def post_shutdown(application):
    """Called on bot shutdown - cleanup resources"""
    await db.close()
    logger.info("🔴 Database connection closed")


def main():
    """Main function to run the bot"""
    
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("new_campaign", new_campaign_command))
    application.add_handler(CommandHandler("campaigns", campaigns_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prices", admin_prices_command))
    application.add_handler(CommandHandler("users", admin_users_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_buy_callback, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(handle_start_campaign, pattern="^start_campaign_"))
    application.add_handler(CallbackQueryHandler(handle_campaign_setup, pattern="^camp_"))
    application.add_handler(CallbackQueryHandler(handle_trunk_callbacks, pattern="^trunk_"))
    application.add_handler(CallbackQueryHandler(handle_lead_callbacks, pattern="^lead_"))
    application.add_handler(CallbackQueryHandler(handle_admin_price_callback, pattern="^price_"))
    application.add_handler(CallbackQueryHandler(handle_menu_callbacks, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(handle_voice_selection, pattern="^voice_"))
    application.add_handler(CallbackQueryHandler(handle_cid_callbacks, pattern="^(cid_|setcid_)"))
    application.add_handler(CallbackQueryHandler(handle_campaign_controls, pattern="^(pause|resume|details|logs)_"))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    # Start bot
    logger.info("🚀 Starting Press-1 IVR Bot (User-Scoped PJSIP)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
