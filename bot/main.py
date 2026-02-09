# =============================================================================
# Telegram Bot - Main Application
# =============================================================================
# Press-1 IVR Bot - Campaign management via Telegram
# =============================================================================

import logging
import csv
import io
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

from config import TELEGRAM_BOT_TOKEN, CREDIT_PACKAGES, ADMIN_TELEGRAM_IDS
# Using mock database for UI testing (no PostgreSQL required)
from database_mock import db
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
    
    # Get or create user in database
    user_data = await db.get_or_create_user(
        user.id,
        user.username,
        user.first_name,
        user.last_name
    )
    
    # Build professional dashboard message
    dashboard_text = f"""
<b>1337 Press One</b>

Hello 1337 P1 150$/1k lines, welcome to the advanced press-one system.

<b>Your Settings</b>
Country Code: {user_data.get('country_code', '+1')} | Caller ID: {user_data.get('caller_id', 'Not Set')}

<b>Account & System Info</b>
Balance: ${user_data.get('balance', 0):.2f} | Available Lines: {user_data.get('available_lines', 0)}
Lines Used: {user_data.get('lines_used', 0)} | System: {user_data.get('system_status', 'Ready')}

Ready to launch your campaign?
"""
    
    # Create 6-button main menu (2x3 grid + bottom row)
    keyboard = [
        [
            InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch"),
            InlineKeyboardButton("💰 Check Balance", callback_data="menu_balance")
        ],
        [
            InlineKeyboardButton("🔧 Configure CID", callback_data="menu_configure_cid"),
            InlineKeyboardButton("📊 Live Statistics", callback_data="menu_statistics")
        ],
        [
            InlineKeyboardButton("🛠️ Tools & Utilities", callback_data="menu_tools"),
            InlineKeyboardButton("🔑 Account Info", callback_data="menu_account")
        ],
        [
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin"),
            InlineKeyboardButton("💬 Contact Support", callback_data="menu_support")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        dashboard_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command with visual indicators"""
    user = update.effective_user
    
    # Get user stats
    stats = await db.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("❌ User not found. Use /start first.")
        return
    
    credits = stats['credits']
    
    # Credit status indicator
    if credits > 100:
        credit_status = "🟢 Excellent"
    elif credits > 50:
        credit_status = "🟡 Good"
    elif credits > 10:
        credit_status = "🟠 Low"
    else:
        credit_status = "🔴 Critical"
    
    balance_text = f"""
💰 **Your Account Balance**
{ui.SEPARATOR_HEAVY}

**Status:** {credit_status}
**Available Credits:** {credits:.2f}

{ui.SEPARATOR_LIGHT}

**Account Statistics:**
💵 Total Spent: ${stats['total_spent']:.2f}
📞 Total Calls: {stats['total_calls']}
📊 Campaigns: {stats['campaign_count']}

{ui.SEPARATOR_LIGHT}

💡 **Pricing:** 1 credit ≈ 1 minute of calling
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Buy More Credits", callback_data="menu_buy")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        balance_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command with modern package cards"""
    
    keyboard = []
    package_items = list(CREDIT_PACKAGES.items())
    
    for i, (package_id, package_data) in enumerate(package_items):
        credits = package_data['credits']
        price = package_data['price']
        currency = package_data['currency']
        
        # Calculate savings for higher packages
        savings = None
        if i > 0:
            base_package = package_items[0][1]
            base_rate = base_package['price'] / base_package['credits']
            current_rate = price / credits
            savings = ((base_rate - current_rate) / base_rate) * 100
        
        # Create package card text
        package_card = ui.package_card(credits, price, currency, savings)
        
        keyboard.append([
            InlineKeyboardButton(
                f"Select {credits} Credits",
                callback_data=f"buy_{package_id}"
            )
        ])
    
    buy_text = f"""
💳 **Purchase Credits**
{ui.SEPARATOR_HEAVY}

**Available Packages:**

"""
    
    # Add package descriptions
    for package_id, package_data in CREDIT_PACKAGES.items():
        credits = package_data['credits']
        price = package_data['price']
        currency = package_data['currency']
        buy_text += ui.package_card(credits, price, currency) + "\n\n"
    
    buy_text += f"""
{ui.SEPARATOR_LIGHT}

**Payment Options:**
✅ Cryptocurrency (USDT, BTC, ETH)
✅ Instant delivery
✅ Secure via Oxapay
✅ No hidden fees

👇 Select a package below:
"""
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        buy_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy package callback"""
    query = update.callback_query
    await query.answer()
    
    # Extract package ID
    package_id = query.data.split('_')[1]
    package = oxapay.get_credit_package(package_id)
    
    if not package:
        await query.edit_message_text("❌ Invalid package")
        return
    
    user = update.effective_user
    
    # Get user from database
    user_data = await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Create payment
    payment_result = await oxapay.create_payment(
        amount=package['price'],
        currency=package['currency'],
        description=f"{package['credits']} credits for IVR Bot"
    )
    
    if not payment_result['success']:
        await query.edit_message_text(
            f"❌ Payment creation failed: {payment_result['error']}"
        )
        return
    
    # Save payment to database
    await db.create_payment(
        user_id=user_data['id'],
        track_id=payment_result['track_id'],
        amount=package['price'],
        credits=package['credits'],
        currency=package['currency'],
        payment_url=payment_result['payment_url']
    )
    
    # Send payment link
    payment_text = f"""
✅ **Payment Created!**

**Package:** {package['credits']} credits
**Amount:** ${package['price']} {package['currency']}
**Track ID:** `{payment_result['track_id']}`

**Payment Link:**
{payment_result['payment_url']}

Click the link above to complete payment.
Credits will be added automatically after confirmation.

⏱️ Payment expires in 30 minutes.
"""
    
    keyboard = [[
        InlineKeyboardButton("💳 Pay Now", url=payment_result['payment_url'])
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        payment_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def new_campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new_campaign command"""
    # Initialize campaign creation flow
    context.user_data['creating_campaign'] = True
    context.user_data['campaign_step'] = 'name'
    
    sent_msg = await update.message.reply_text(
        """
📝 <b>Create New Campaign</b>

Step 1: What would you like to name this campaign?

Example: Product Launch 2026
""",
        parse_mode='HTML'
    )
    
    # Store message ID for cleanup
    context.user_data['last_bot_message'] = sent_msg.message_id


async def campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /campaigns command with modern campaign cards"""
    user = update.effective_user
    
    # Get user from database
    user_data = await db.get_or_create_user(user.id)
    
    # Get campaigns
    campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
    
    if not campaigns:
        empty_text = f"""
📂 **No Campaigns Yet**
{ui.SEPARATOR_LIGHT}

You haven't created any campaigns yet.

Ready to start? Create your first campaign now! 🚀
"""
        keyboard = [
            [InlineKeyboardButton("📝 Create Campaign", callback_data="menu_new_campaign")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            empty_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Build modern campaign list with cards
    campaigns_text = f"""
📊 **Your Campaigns**
{ui.SEPARATOR_HEAVY}

Showing {len(campaigns)} most recent campaigns:

"""
    
    keyboard = []
    for camp in campaigns:
        # Add campaign card
        campaigns_text += ui.campaign_card(camp) + "\n\n"
        
        # Add action buttons for each campaign
        campaign_id = camp['id']
        status = camp['status']
        
        if status == 'running':
            keyboard.append([
                InlineKeyboardButton(
                    f"⏸️ Pause '{camp['name'][:20]}'",
                    callback_data=f"pause_{campaign_id}"
                ),
                InlineKeyboardButton(
                    "📊 Details",
                    callback_data=f"details_{campaign_id}"
                )
            ])
        elif status == 'paused':
            keyboard.append([
                InlineKeyboardButton(
                    f"▶️ Resume '{camp['name'][:20]}'",
                    callback_data=f"resume_{campaign_id}"
                ),
                InlineKeyboardButton(
                    "📊 Details",
                    callback_data=f"details_{campaign_id}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    f"📊 View '{camp['name'][:20]}'",
                    callback_data=f"details_{campaign_id}"
                )
            ])
    
    # Add bottom buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="menu_campaigns"),
        InlineKeyboardButton("🔙 Menu", callback_data="menu_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        campaigns_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
❓ <b>Help & Support</b>

<b>Commands:</b>
/start - Start the bot
/balance - Check your credits
/buy - Purchase credits
/new_campaign - Create new campaign
/campaigns - View all campaigns
/help - Show this help

<b>Campaign Creation:</b>
1. Use /new_campaign
2. Give it a name
3. Upload CSV file with phone numbers
4. Start the campaign

<b>CSV Format:</b>
Your CSV should have phone numbers in the first column:

1234567890
9876543210
5555555555

<b>Pricing:</b>
• 1 credit ≈ 1 minute of calling
• Minimum 6 seconds billing
• 6-second increments

<b>Support:</b>
If you need help, contact: @your_support_username

<b>Technical Info:</b>
• Powered by Asterisk PBX
• MagnusBilling trunk provider
• Oxapay payment processing
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during campaign creation"""
    
    user = update.effective_user
    
    # Handle custom CID input
    if context.user_data.get('awaiting_custom_cid'):
        cid = update.message.text.strip()
        
        # Validate CID
        is_valid, message = await db.validate_cid(cid)
        
        if is_valid:
            # Clean CID and set it
            clean_cid = ''.join(filter(str.isdigit, cid))
            await db.set_caller_id(user.id, clean_cid)
            
            # Clear awaiting flag
            context.user_data['awaiting_custom_cid'] = False
            
            await update.message.reply_text(
                f"""
✅ <b>CID Set Successfully</b>

Your Caller ID has been set to: {clean_cid}

This CID will be used for all your campaigns.
""",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")
                ]])
            )
        else:
            await update.message.reply_text(
                f"""
❌ <b>CID Validation Failed</b>

{message}

Please try again or /cancel.
""",
                parse_mode='HTML'
            )
        return
    
    if not context.user_data.get('creating_campaign'):
        return
    
    step = context.user_data.get('campaign_step')
    
    if step == 'name':
        # Save campaign name
        campaign_name = update.message.text
        
        # Get user from database
        user_data = await db.get_or_create_user(user.id)
        
        # Create campaign
        campaign_id = await db.create_campaign(
            user_id=user_data['id'],
            name=campaign_name
        )
        
        context.user_data['campaign_id'] = campaign_id
        context.user_data['campaign_name'] = campaign_name
        context.user_data['campaign_step'] = 'voice_choice'
        
        # Delete the name question message if stored
        if 'last_bot_message' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # Get saved voice files
        saved_voices = await db.get_user_voice_files(user_data['id'])
        
        # Show voice selection options
        keyboard = []
        
        if saved_voices:
            # Add saved voice files
            for voice in saved_voices[:5]:  # Show max 5
                keyboard.append([InlineKeyboardButton(
                    f"🎤 {voice['name']} ({voice['duration']}s)",
                    callback_data=f"voice_select_{voice['id']}"
                )])
        
        # Add upload new option
        keyboard.append([InlineKeyboardButton(
            "📤 Upload New Voice File",
            callback_data="voice_upload_new"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_msg = await update.message.reply_text(
            f"""
✅ <b>Campaign Created!</b>

Name: {campaign_name}

Step 2: Select or Upload IVR Audio

<b>Choose an option:</b>
• Select from your saved voice files
• Or upload a new one

""",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        # Store this message to potentially delete later
        context.user_data['last_bot_message'] = sent_msg.message_id




async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice/audio file upload for IVR"""
    
    if not context.user_data.get('creating_campaign'):
        await update.message.reply_text("Please use /new_campaign first")
        return
    
    if context.user_data.get('campaign_step') != 'voice_upload':
        return
    
    user = update.effective_user
    
    # Get voice file info
    if update.message.voice:
        file = update.message.voice
        file_type = "voice message"
        duration = file.duration or 30
    elif update.message.audio:
        file = update.message.audio
        file_type = "audio file"
        duration = file.duration or 30
    else:
        return
    
    # Save the voice file to database
    user_data = await db.get_or_create_user(user.id)
    campaign_name = context.user_data.get('campaign_name', 'Voice')
    voice_name = f"{campaign_name} - Voice"
    
    voice_id = await db.save_voice_file(user_data['id'], voice_name, duration)
    
    # Move to next step
    context.user_data['campaign_step'] = 'upload'
    context.user_data['voice_id'] = voice_id
    
    # Send single consolidated message
    await update.message.reply_text(
        f"""
✅ <b>Voice File Saved!</b>

📝 {voice_name} ({duration}s)

━━━━━━━━━━━━━━━━━━━━━━

📂 <b>Step 3: Upload Phone Numbers</b>

Send a CSV or TXT file with phone numbers (one per line)

Example:
1234567890
9876543210
""",
        parse_mode='HTML'
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CSV/TXT file upload"""
    
    if not context.user_data.get('creating_campaign'):
        await update.message.reply_text("Please use /new_campaign first")
        return
    
    if context.user_data.get('campaign_step') != 'upload':
        return
    
    user = update.effective_user
    file = await update.message.document.get_file()
    
    # Check file extension
    filename = update.message.document.file_name.lower()
    if not (filename.endswith('.csv') or filename.endswith('.txt')):
        await update.message.reply_text(
            "❌ Please upload a CSV or TXT file\n\nSupported formats: .csv, .txt"
        )
        return
    
    # Download file
    file_content = await file.download_as_bytearray()
    
    # Parse file
    try:
        text_content = file_content.decode('utf-8')
        phone_numbers = []
        
        if filename.endswith('.csv'):
            # Parse CSV
            reader = csv.reader(io.StringIO(text_content))
            for row in reader:
                if row and row[0].strip():
                    # Clean phone number
                    phone = ''.join(filter(str.isdigit, row[0]))
                    if phone:
                        phone_numbers.append(phone)
        else:  # TXT file
            # Parse TXT - each line is a phone number
            lines = text_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    # Clean phone number
                    phone = ''.join(filter(str.isdigit, line))
                    if phone:
                        phone_numbers.append(phone)
        
        if not phone_numbers:
            await update.message.reply_text("❌ No valid phone numbers found in file")
            return
        
        # Add to campaign
        campaign_id = context.user_data['campaign_id']
        count = await db.add_campaign_numbers(campaign_id, phone_numbers)
        
        # Clear creation state
        context.user_data['creating_campaign'] = False
        
        # Show campaign ready message
        keyboard = [[
            InlineKeyboardButton(
                "🚀 Start Campaign",
                callback_data=f"start_campaign_{campaign_id}"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"""
✅ <b>Campaign Ready!</b>

📊 <b>Numbers uploaded:</b> {count}
💰 <b>Estimated cost:</b> ~${count * 1.0:.2f}

Your campaign is ready to launch!
Click the button below to start calling.
""",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await update.message.reply_text(
            f"❌ Error processing file: {str(e)}\n\nPlease make sure it's a valid CSV or TXT file."
        )


async def handle_start_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start campaign callback"""
    query = update.callback_query
    await query.answer()
    
    # Extract campaign ID
    campaign_id = int(query.data.split('_')[2])
    
    # Start campaign
    await db.start_campaign(campaign_id)
    
    await query.edit_message_text(
        f"""
🚀 **Campaign Started!**
{ui.SEPARATOR_MEDIUM}

Campaign ID: {campaign_id}

Your campaign is now running. Calls are being made automatically.

{ui.SEPARATOR_LIGHT}

💡 **What's happening:**
• Phone numbers are being dialed automatically
• IVR message plays when answered
• DTMF detection tracks who presses '1'
• Credits are deducted for answered calls

Use /campaigns to check real-time progress.
""",
        parse_mode='Markdown'
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
        # Return to main dashboard
        dashboard_text = f"""
<b>1337 Press One</b>

Hello 1337 P1 150$/1k lines, welcome to the advanced press-one system.

<b>Your Settings</b>
Country Code: {user_data.get('country_code', '+1')} | Caller ID: {user_data.get('caller_id', 'Not Set')}

<b>Account & System Info</b>
Balance: ${user_data.get('balance', 0):.2f} | Available Lines: {user_data.get('available_lines', 0)}
Lines Used: {user_data.get('lines_used', 0)} | System: {user_data.get('system_status', 'Ready')}

Ready to launch your campaign?
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch"),
                InlineKeyboardButton("💰 Check Balance", callback_data="menu_balance")
            ],
            [
                InlineKeyboardButton("🔧 Configure CID", callback_data="menu_configure_cid"),
                InlineKeyboardButton("📊 Live Statistics", callback_data="menu_statistics")
            ],
            [
                InlineKeyboardButton("🛠️ Tools & Utilities", callback_data="menu_tools"),
                InlineKeyboardButton("🔑 Account Info", callback_data="menu_account")
            ],
            [
                InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin"),
                InlineKeyboardButton("💬 Contact Support", callback_data="menu_support")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            dashboard_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "launch":
        # Launch Campaign - simplified flow
        # Check balance first
        balance = user_data.get('balance', 0)
        if balance <= 0:
            await query.edit_message_text(
                "❌ You don't have enough credits.\\nPlease add credits to continue.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💰 Add Credits", callback_data="menu_balance"),
                    InlineKeyboardButton("🔙 Back", callback_data="menu_main")
                ]])
            )
            return
        
        # Start campaign creation
        context.user_data['creating_campaign'] = True
        context.user_data['campaign_step'] = 'name'
        
        await query.edit_message_text(
            """
📝 <b>Create New Campaign</b>

Step 1: What would you like to name this campaign?

Example: Product Launch 2026
""",
            parse_mode='HTML'
        )
    
    elif action == "balance":
        # Check Balance view
        balance = user_data.get('balance', 0)
        available_lines = user_data.get('available_lines', 0)
        lines_used = user_data.get('lines_used', 0)
        
        balance_text = f"""
💰 <b>Account Balance</b>

<b>Current Balance:</b> ${balance:.2f}
<b>Available Lines:</b> {available_lines}
<b>Lines Used:</b> {lines_used}

<b>Pricing:</b>
• 150$/1k lines
• Bulk discounts available
• Pay as you go

Need more credits? Contact support!
"""
        
        keyboard = [
            [InlineKeyboardButton("💬 Contact Support", callback_data="menu_support")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            balance_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "configure_cid":
        # Caller ID Management Menu
        current_cid = user_data.get('caller_id', 'Not Set')
        
        cid_text = f"""
🔧 <b>Caller ID Management</b>

Configure your caller identification for optimal campaign performance.

<b>Current Setup</b>
Active CID: {current_cid}

<b>Configuration Options</b>
Preset CIDs - Verified, high-performance numbers
Custom CID - Use your own number with validation

All caller IDs are validated against our blacklist for compliance.
"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Preset CIDs", callback_data="cid_preset")],
            [InlineKeyboardButton("✏️ Custom CID", callback_data="cid_custom")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            cid_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "statistics":
        # Live Statistics view
        campaigns = await db.get_user_campaigns(user_data['id'], limit=5)
        total_campaigns = len(campaigns)
        total_calls = user_data.get('total_calls', 0)
        
        stats_text = f"""
📊 <b>Live Statistics</b>

<b>Your Campaign Stats</b>
Total Campaigns: {total_campaigns}
Total Calls Made: {total_calls}
Lines Used: {user_data.get('lines_used', 0)}

<b>Recent Activity</b>
"""
        
        # Add recent campaigns
        if campaigns:
            for camp in campaigns[:3]:
                stats_text += f"\n• {camp.get('name', 'Unnamed')} - {camp.get('status', 'Unknown')}"
        else:
            stats_text += "\nNo campaigns yet"
        
        keyboard = [
            [InlineKeyboardButton("📊 View All Campaigns", callback_data="menu_campaigns")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "tools":
        # Tools & Utilities menu
        tools_text = """
🛠️ <b>Tools & Utilities</b>

<b>Available Tools:</b>

• CSV Validator - Check your phone lists
• Number Formatter - Format phone numbers
• DNC Checker - Check Do Not Call list
• Campaign Scheduler - Schedule campaigns

More tools coming soon!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            tools_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "account":
        # Account Info view
        account_text = f"""
🔑 <b>Account Information</b>

<b>Account Details</b>
Username: @{user.username or 'Not set'}
User ID: {user.id}
Country Code: {user_data.get('country_code', '+1')}

<b>Account Settings</b>
Caller ID: {user_data.get('caller_id', 'Not Set')}
Balance: ${user_data.get('balance', 0):.2f}
Status: {user_data.get('system_status', 'Ready')}

<b>Usage Stats</b>
Available Lines: {user_data.get('available_lines', 0)}
Lines Used: {user_data.get('lines_used', 0)}
Total Calls: {user_data.get('total_calls', 0)}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            account_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "admin":
        # Admin Panel
        admin_text = """
⚙️ <b>Admin Panel</b>

<b>System Administration</b>

• User Management
• System Configuration
• Reports & Analytics
• Billing Management

Contact support for admin access.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            admin_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "support":
        # Contact Support
        support_text = """
💬 <b>Contact Support</b>

<b>Need Help?</b>

Our support team is here 24/7 to assist you.

<b>Contact Methods:</b>
📧 Email: support@1337.com
💬 Telegram: @1337Support
📞 Phone: +1 (555) 123-4567

<b>Response Time:</b>
Average: 2-4 hours
Priority: Under 1 hour

We're here to help!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            support_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "campaigns":
        # Show campaigns list (keeping existing functionality)
        campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
        
        if not campaigns:
            empty_text = """
📂 <b>No Campaigns Yet</b>

You haven't created any campaigns yet.

Ready to start? Create your first campaign now! 🚀
"""
            keyboard = [
                [InlineKeyboardButton("🚀 Launch Campaign", callback_data="menu_launch")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                empty_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
        
        # Build campaigns list
        campaigns_text = f"""
📊 <b>My Campaigns</b>

<b>Active Campaigns: {len([c for c in campaigns if c.get('status') == 'running'])}</b>

"""
        
        keyboard = []
        for campaign in campaigns:
            status_emoji = {
                'running': '🟢',
                'paused': '🟡',
                'completed': '✅',
                'failed': '❌'
            }.get(campaign.get('status', ''), '⚪')
            
            campaigns_text += f"{status_emoji} {campaign.get('name', 'Unnamed')}\n"
            keyboard.append([InlineKeyboardButton(
                f"📊 {campaign.get('name', 'Unnamed')}",
                callback_data=f"details_{campaign['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            campaigns_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    """Handle main menu navigation callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("menu_", "")
    user = update.effective_user
    
    if action == "main":
        # Show main menu
        user_data = await db.get_or_create_user(user.id)
        welcome_text = ui.main_menu_text(user_data)
        
        keyboard = [
            [InlineKeyboardButton("💳 Buy Credits", callback_data="menu_buy")],
            [InlineKeyboardButton("📝 New Campaign", callback_data="menu_new_campaign")],
            [InlineKeyboardButton("📊 My Campaigns", callback_data="menu_campaigns")],
            [
                InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif action == "balance":
        # Show balance - call balance handler logic
        stats = await db.get_user_stats(user.id)
        
        if not stats:
            await query.edit_message_text("❌ User not found. Use /start first.")
            return
        
        credits = stats['credits']
        
        if credits > 100:
            credit_status = "🟢 Excellent"
        elif credits > 50:
            credit_status = "🟡 Good"
        elif credits > 10:
            credit_status = "🟠 Low"
        else:
            credit_status = "🔴 Critical"
        
        balance_text = f"""
💰 **Your Account Balance**
{ui.SEPARATOR_HEAVY}

**Status:** {credit_status}
**Available Credits:** {credits:.2f}

{ui.SEPARATOR_LIGHT}

**Account Statistics:**
💵 Total Spent: ${stats['total_spent']:.2f}
📞 Total Calls: {stats['total_calls']}
📊 Campaigns: {stats['campaign_count']}

{ui.SEPARATOR_LIGHT}

💡 **Pricing:** 1 credit ≈ 1 minute of calling
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Buy More Credits", callback_data="menu_buy")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            balance_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif action == "buy":
        # Show buy credits menu - simplified version
        keyboard = []
        package_items = list(CREDIT_PACKAGES.items())
        
        buy_text = f"""
💳 **Purchase Credits**
{ui.SEPARATOR_HEAVY}

**Available Packages:**

"""
        
        for package_id, package_data in CREDIT_PACKAGES.items():
            credits = package_data['credits']
            price = package_data['price']
            currency = package_data['currency']
            buy_text += ui.package_card(credits, price, currency) + "\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"Select {credits} Credits",
                    callback_data=f"buy_{package_id}"
                )
            ])
        
        buy_text += f"""
{ui.SEPARATOR_LIGHT}

**Payment Options:**
✅ Cryptocurrency (USDT, BTC, ETH)
✅ Instant delivery
✅ Secure via Oxapay
✅ No hidden fees

👇 Select a package below:
"""
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            buy_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif action == "campaigns":
        # Show campaigns list
        user_data = await db.get_or_create_user(user.id)
        campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
        
        if not campaigns:
            empty_text = f"""
📂 **No Campaigns Yet**
{ui.SEPARATOR_LIGHT}

You haven't created any campaigns yet.

Ready to start? Create your first campaign now! 🚀
"""
            keyboard = [
                [InlineKeyboardButton("📝 Create Campaign", callback_data="menu_new_campaign")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                empty_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        campaigns_text = f"""
📊 **Your Campaigns**
{ui.SEPARATOR_HEAVY}

Showing {len(campaigns)} most recent campaigns:

"""
        
        keyboard = []
        for camp in campaigns:
            campaigns_text += ui.campaign_card(camp) + "\n\n"
            
            campaign_id = camp['id']
            status = camp['status']
            
            if status == 'running':
                keyboard.append([
                    InlineKeyboardButton(
                        f"⏸️ Pause '{camp['name'][:20]}'",
                        callback_data=f"pause_{campaign_id}"
                    ),
                    InlineKeyboardButton(
                        "📊 Details",
                        callback_data=f"details_{campaign_id}"
                    )
                ])
            elif status == 'paused':
                keyboard.append([
                    InlineKeyboardButton(
                        f"▶️ Resume '{camp['name'][:20]}'",
                        callback_data=f"resume_{campaign_id}"
                    ),
                    InlineKeyboardButton(
                        "📊 Details",
                        callback_data=f"details_{campaign_id}"
                    )
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📊 View '{camp['name'][:20]}'",
                        callback_data=f"details_{campaign_id}"
                    )
                ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="menu_campaigns"),
            InlineKeyboardButton("🔙 Menu", callback_data="menu_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            campaigns_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    
    elif action == "new_campaign":
        # Start new campaign creation flow
        # Set up user context for campaign creation
        context.user_data['creating_campaign'] = True
        context.user_data['campaign_step'] = 'name'
        
        await query.edit_message_text(
            """
📝 <b>Create New Campaign</b>

Step 1: What would you like to name this campaign?

Example: Product Launch 2026
""",
            parse_mode='HTML'
        )
    
    elif action == "help":
        help_text = f"""
❓ <b>Help & Support</b>
{ui.SEPARATOR_HEAVY}

<b>Commands:</b>
/start - Start the bot
/balance - Check your credits
/buy - Purchase credits
/new_campaign - Create new campaign
/campaigns - View all campaigns
/help - Show this help

{ui.SEPARATOR_LIGHT}

<b>Campaign Creation:</b>
1. Use /new_campaign
2. Give it a name
3. Upload CSV file with phone numbers
4. Start the campaign

{ui.SEPARATOR_LIGHT}

<b>CSV Format:</b>
Your CSV should have phone numbers in the first column:

1234567890
9876543210
5555555555

{ui.SEPARATOR_LIGHT}

<b>Pricing:</b>
• 1 credit ≈ 1 minute of calling
• Minimum 6 seconds billing
• 6-second increments

<b>Technical Info:</b>
• Powered by Asterisk PBX
• MagnusBilling trunk provider
• Oxapay payment processing
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )




# =============================================================================
# Caller ID Management Callbacks
# =============================================================================

async def handle_cid_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Caller ID configuration callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "cid_preset":
        # Show preset CIDs list
        preset_cids = await db.get_preset_cids()
        
        cid_list_text = """
📋 <b>Preset Caller IDs</b>

Select a verified, high-performance caller ID:

"""
        
        keyboard = []
        for cid in preset_cids:
            cid_list_text += f"• {cid['name']}: {cid['number']}\n"
            keyboard.append([InlineKeyboardButton(
                f"✅ {cid['name']}",
                callback_data=f"setcid_{cid['number']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_configure_cid")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            cid_list_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif data == "cid_custom":
        # Initiate custom CID input
        context.user_data['awaiting_custom_cid'] = True
        
        await query.edit_message_text(
            """
✏️ <b>Set Custom Caller ID</b>

Send me your desired CID as a message.

<b>Format:</b> Just the numbers (e.g., 15551234567)
<b>Length:</b> 10-15 digits

⚠️ <b>Your CID will be validated against our blacklist for compliance.</b>

Type /cancel to cancel.
""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="menu_configure_cid")
            ]])
        )
    
    elif data.startswith("setcid_"):
        # Set selected CID
        cid = data.replace("setcid_", "")
        await db.set_caller_id(user.id, cid)
        
        await query.edit_message_text(
            f"""
✅ <b>CID Set Successfully</b>

Your Caller ID has been set to: {cid}

This CID will be used for all your campaigns.
""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")
            ]])
        )


# =============================================================================
# Campaign Control Callbacks
# =============================================================================



async def handle_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice file selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "voice_upload_new":
        # User wants to upload new voice file
        context.user_data['campaign_step'] = 'voice_upload'
        
        await query.edit_message_text(
            """
🎤 <b>Upload New Voice File</b>

Please send your IVR audio message now.

<b>Supported Formats:</b>
• Voice messages
• Audio files (MP3, WAV, OGG)
• Max duration: 60 seconds

Send the file now →
""",
            parse_mode='HTML'
        )
    
    elif data.startswith("voice_select_"):
        # User selected an existing voice file
        voice_id = int(data.split("_")[-1])
        context.user_data['voice_id'] = voice_id
        context.user_data['campaign_step'] = 'upload'
        
        # Get voice file info
        voice = await db.get_voice_file(voice_id)
        
        await query.edit_message_text(
            f"""
✅ <b>Voice File Selected!</b>

📝 {voice.get('name', 'Unknown')}
⏱️ Duration: {voice.get('duration', 0)}s

Step 3: Upload Phone Numbers

Upload your phone numbers as a CSV file.

<b>CSV Format:</b>
One phone number per line

Example:
1234567890
9876543210
5555555555

Send the CSV file now →
""",
            parse_mode='HTML'
        )


async def handle_campaign_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle campaign pause/resume/details/logs callbacks"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    campaign_id = int(parts[1])
    
    if action == "pause":
        # Pause campaign
        await db.stop_campaign(campaign_id)
        await query.answer("⏸️ Campaign paused")
        
        # Refresh campaigns list
        query.data = "menu_campaigns"
        await handle_menu_callbacks(update, context)
    
    elif action == "resume":
        # Resume campaign
        await db.start_campaign(campaign_id)
        await query.answer("▶️ Campaign resumed")
        
        # Refresh campaigns list
        query.data = "menu_campaigns"
        await handle_menu_callbacks(update, context)
    
    elif action == "logs":
        # Show detailed call logs
        call_logs = await db.get_campaign_call_logs(campaign_id, limit=20)
        stats = await db.get_campaign_stats(campaign_id)
        
        logs_text = f"""
📋 <b>Call Logs</b> - {stats.get('name', 'Campaign')}

━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for i, log in enumerate(call_logs, 1):
            # Status emoji
            if log['status'] == 'pressed_one':
                status_icon = "✅"
                status_text = "PRESSED 1"
            elif log['status'] == 'answered':
                status_icon = "📞"
                status_text = "Answered"
            elif log['status'] == 'no_answer':
                status_icon = "⭕"
                status_text = "No Answer"
            else:
                status_icon = "❌"
                status_text = "Failed"
            
            # Format timestamp
            from datetime import datetime # Assuming datetime needs to be imported
            time_ago = datetime.now() - log['timestamp']
            if time_ago.seconds < 60:
                time_str = f"{time_ago.seconds}s ago"
            elif time_ago.seconds < 3600:
                time_str = f"{time_ago.seconds // 60}m ago"
            else:
                time_str = f"{time_ago.seconds // 3600}h ago"
            
            logs_text += f"""
{i}. {status_icon} <b>{status_text}</b>
   📱 {log['phone_number']}
   ⏱️ {log.get('duration', 0)}s • 💰 ${log.get('cost', 0):.2f}
   🕒 {time_str}

"""
        
        logs_text += """
━━━━━━━━━━━━━━━━━━━━━━

<b>Legend:</b>
✅ = Pressed 1 (Success!)
📞 = Answered
⭕ = No answer
❌ = Failed
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Summary", callback_data=f"details_{campaign_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            logs_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif action == "details":
        # Show campaign summary in clean format
        stats = await db.get_campaign_stats(campaign_id)
        
        if not stats:
            await query.edit_message_text("❌ Campaign not found")
            return
        
        # Calculate stats
        total = stats.get('total_numbers', 0)
        completed = stats.get('completed', 0)
        pressed_one = stats.get('pressed_one', 0)
        answered = stats.get('answered', 0)
        voicemails = 0  # Mock data doesn't have this yet
        
        # Calculate rates
        progress_pct = (completed / total * 100) if total > 0 else 0
        p1_rate = (pressed_one / answered * 100) if answered > 0 else 0
        voicemail_rate = (voicemails / completed * 100) if completed > 0 else 0
        remaining = total - completed
        
        # Create progress bar
        bar_length = 10
        filled = int((completed / total) * bar_length) if total > 0 else 0
        progress_bar = "█" * filled + "░" * (bar_length - filled)
        
        # Format message in clean style
        details_text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📊 {stats.get('name', 'Campaign').upper()} ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🎯 <b>RESULTS:</b>
💎 Pressed 1: {pressed_one}
💼 Total: {completed}
📞 Voicemails: {voicemails}

⚡ <b>PROGRESS:</b>
[{progress_bar}] {progress_pct:.1f}% ({completed}/{total})
⏳ Remaining: {remaining}
🎯 P1 Rate: {p1_rate:.2f}%
📞 Voicemail Rate: {voicemail_rate:.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Cost: ${stats.get('actual_cost', 0):.2f}
📊 Status: {ui.status_badge(stats.get('status', 'unknown'))}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📋 View Call Logs", callback_data=f"logs_{campaign_id}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"details_{campaign_id}")
            ],
            [InlineKeyboardButton("🔙 Back to Campaigns", callback_data="menu_campaigns")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            details_text,
            parse_mode='HTML',
            reply_markup=reply_markup
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


def main():
    """Main function to run the bot"""
    
    # Create application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("new_campaign", new_campaign_command))
    application.add_handler(CommandHandler("campaigns", campaigns_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add callback handlers
    application.add_handler(
        CallbackQueryHandler(handle_buy_callback, pattern="^buy_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_start_campaign, pattern="^start_campaign_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_menu_callbacks, pattern="^menu_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_voice_selection, pattern="^voice_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_cid_callbacks, pattern="^(cid_|setcid_)")
    )
    application.add_handler(
        CallbackQueryHandler(handle_campaign_controls, pattern="^(pause|resume|details|logs)_")
    )
    
    # Add message handlers
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO, handle_voice)
    )
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_file)
    )
    
    # Start bot
    logger.info("🚀 Starting Press-1 IVR Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
