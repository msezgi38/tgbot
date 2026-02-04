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
from database import db
from oxapay_handler import oxapay

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# =============================================================================
# Command Handlers
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Get or create user in database
    user_data = await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = f"""
🤖 **Welcome to Press-1 IVR Bot!**

Hello {user.first_name}! 👋

This bot helps you run automated Press-1 IVR campaigns to reach thousands of people.

**How it works:**
1️⃣ Buy credits using cryptocurrency
2️⃣ Upload your contact list (CSV)
3️⃣ Start your campaign
4️⃣ Get real-time results

**Available Commands:**
/balance - Check your credits
/buy - Purchase credits
/new_campaign - Create new campaign
/campaigns - View your campaigns
/help - Get help

**Your Account:**
💰 Credits: {user_data['credits']:.2f}
📞 Total Calls: {user_data['total_calls']}

Ready to get started? Use /buy to purchase credits!
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown'
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    user = update.effective_user
    
    # Get user stats
    stats = await db.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("❌ User not found. Use /start first.")
        return
    
    balance_text = f"""
💰 **Your Account Balance**

**Available Credits:** {stats['credits']:.2f}
**Total Spent:** ${stats['total_spent']:.2f}
**Total Calls:** {stats['total_calls']}
**Total Campaigns:** {stats['campaign_count']}

**Pricing:** 1 credit = ~1 minute of calling

Need more credits? Use /buy
"""
    
    await update.message.reply_text(
        balance_text,
        parse_mode='Markdown'
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command - show credit packages"""
    
    keyboard = []
    for package_id, package_data in CREDIT_PACKAGES.items():
        credits = package_data['credits']
        price = package_data['price']
        currency = package_data['currency']
        
        button_text = f"💎 {credits} Credits - ${price} {currency}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"buy_{package_id}"
            )
        ])
    
    buy_text = """
💳 **Purchase Credits**

Select a package to continue:

**What you get:**
✅ Instant credit delivery
✅ Pay with cryptocurrency (USDT, BTC, ETH)
✅ Secure payment via Oxapay
✅ No hidden fees

Choose your package below:
"""
    
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
    user = update.effective_user
    
    # Get user from database
    user_data = await db.get_or_create_user(user.id)
    
    if user_data['credits'] <= 0:
        await update.message.reply_text(
            "❌ You don't have enough credits.\nUse /buy to purchase credits first."
        )
        return
    
    # Store state in context
    context.user_data['creating_campaign'] = True
    context.user_data['campaign_step'] = 'name'
    
    await update.message.reply_text(
        """
📝 **Create New Campaign**

Step 1: What would you like to name this campaign?

Example: "Product Launch 2026"
"""
    )


async def campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /campaigns command - list user's campaigns"""
    user = update.effective_user
    
    # Get user from database
    user_data = await db.get_or_create_user(user.id)
    
    # Get campaigns
    campaigns = await db.get_user_campaigns(user_data['id'], limit=10)
    
    if not campaigns:
        await update.message.reply_text(
            "📂 You don't have any campaigns yet.\n\nUse /new_campaign to create one!"
        )
        return
    
    # Build campaign list
    campaigns_text = "📊 **Your Campaigns**\n\n"
    
    for camp in campaigns:
        status_emoji = {
            'draft': '📝',
            'running': '🚀',
            'paused': '⏸️',
            'completed': '✅'
        }.get(camp['status'], '❓')
        
        campaigns_text += f"{status_emoji} **{camp['name']}**\n"
        campaigns_text += f"   • Numbers: {camp['total_numbers']}\n"
        campaigns_text += f"   • Completed: {camp['completed']}\n"
        campaigns_text += f"   • Success: {camp['pressed_one']}\n"
        campaigns_text += f"   • Cost: ${camp['actual_cost']:.2f}\n"
        campaigns_text += f"   • Status: {camp['status']}\n"
        campaigns_text += f"   • /campaign_{camp['id']}\n\n"
    
    await update.message.reply_text(
        campaigns_text,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
❓ **Help & Support**

**Commands:**
/start - Start the bot
/balance - Check your credits
/buy - Purchase credits
/new_campaign - Create new campaign
/campaigns - View all campaigns
/help - Show this help

**Campaign Creation:**
1. Use /new_campaign
2. Give it a name
3. Upload CSV file with phone numbers
4. Start the campaign

**CSV Format:**
Your CSV should have phone numbers in the first column:
```
1234567890
9876543210
5555555555
```

**Pricing:**
- 1 credit ≈ 1 minute of calling
- Minimum 6 seconds billing
- 6-second increments

**Support:**
If you need help, contact: @your_support_username

**Technical Info:**
- Powered by Asterisk PBX
- MagnusBilling trunk provider
- Oxapay payment processing
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during campaign creation"""
    
    if not context.user_data.get('creating_campaign'):
        await update.message.reply_text(
            "I didn't understand that. Use /help to see available commands."
        )
        return
    
    user = update.effective_user
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
        context.user_data['campaign_step'] = 'upload'
        
        await update.message.reply_text(
            f"""
✅ Campaign "{campaign_name}" created!

Step 2: Upload your phone numbers as a CSV file.

**CSV Format:**
```
1234567890
9876543210
5555555555
```

Send the CSV file now →
"""
        )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CSV file upload"""
    
    if not context.user_data.get('creating_campaign'):
        await update.message.reply_text("Please use /new_campaign first")
        return
    
    if context.user_data.get('campaign_step') != 'upload':
        return
    
    user = update.effective_user
    file = await update.message.document.get_file()
    
    # Download file
    file_content = await file.download_as_bytearray()
    
    # Parse CSV
    try:
        csv_text = file_content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        
        phone_numbers = []
        for row in reader:
            if row and row[0].strip():
                # Clean phone number
                phone = ''.join(filter(str.isdigit, row[0]))
                if phone:
                    phone_numbers.append(phone)
        
        if not phone_numbers:
            await update.message.reply_text("❌ No valid phone numbers found in CSV")
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
✅ **Campaign Ready!**

📊 **Numbers uploaded:** {count}
💰 **Estimated cost:** ~{count} credits

Your campaign is ready to launch!
Click the button below to start calling.
""",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        await update.message.reply_text(
            f"❌ Error processing CSV file: {str(e)}\nPlease make sure it's a valid CSV."
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

Campaign ID: {campaign_id}

Your campaign is now running. You'll receive updates as calls are made.

Use /campaigns to check progress.
""",
        parse_mode='Markdown'
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
    
    # Add message handlers
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_file)
    )
    
    # Start bot
    logger.info("🚀 Starting Press-1 IVR Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
