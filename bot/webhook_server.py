# =============================================================================
# Webhook Server - Oxapay Payment Callbacks
# =============================================================================
# HTTP server that receives payment status updates from Oxapay
# Activates subscriptions and credits when payments are confirmed
# =============================================================================

import logging
import json
from aiohttp import web
from datetime import datetime

logger = logging.getLogger(__name__)


class WebhookServer:
    """HTTP server for receiving Oxapay payment webhooks"""
    
    def __init__(self, db, bot_app=None, host="0.0.0.0", port=8000):
        self.db = db
        self.bot_app = bot_app  # telegram bot application for sending messages
        self.host = host
        self.port = port
        self.runner = None
    
    async def start(self):
        """Start the webhook HTTP server"""
        app = web.Application()
        app.router.add_post('/webhook/oxapay', self.handle_oxapay_webhook)
        app.router.add_get('/health', self.handle_health)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        logger.info(f"🌐 Webhook server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the webhook server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("🔴 Webhook server stopped")
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({"status": "ok", "time": datetime.now().isoformat()})
    
    async def handle_oxapay_webhook(self, request):
        """
        Handle Oxapay payment webhook callback.
        
        Oxapay sends POST with JSON body containing payment status updates.
        Key fields:
        - trackId: our payment tracking ID
        - status: "Waiting", "Confirming", "Paid", "Failed", "Expired"
        - amount: payment amount
        - txID: blockchain transaction hash
        """
        try:
            # Parse webhook data
            try:
                data = await request.json()
            except Exception:
                body = await request.text()
                logger.warning(f"⚠️ Webhook: Non-JSON body received: {body[:500]}")
                return web.json_response({"error": "Invalid JSON"}, status=400)
            
            logger.info(f"📨 Oxapay webhook received: {json.dumps(data, default=str)}")
            
            track_id = data.get('trackId') or data.get('track_id') or data.get('orderId')
            status = data.get('status', '').lower()
            tx_hash = data.get('txID') or data.get('tx_hash', '')
            
            if not track_id:
                logger.warning("⚠️ Webhook: No trackId in data")
                return web.json_response({"error": "No trackId"}, status=400)
            
            logger.info(f"📋 Webhook: trackId={track_id}, status={status}, txHash={tx_hash}")
            
            # Only process completed payments
            if status in ('paid', 'complete', 'completed', 'confirmed'):
                await self._handle_paid(track_id, tx_hash)
            elif status in ('failed', 'expired', 'canceled'):
                logger.info(f"❌ Payment {track_id} {status}")
            else:
                logger.info(f"⏳ Payment {track_id} status: {status} (waiting)")
            
            return web.json_response({"status": "ok"})
            
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_paid(self, track_id: str, tx_hash: str = ""):
        """Process a confirmed payment — activate subscription or add credits"""
        
        # 1. Check if this is a subscription payment
        sub = await self.db.get_subscription_by_track_id(track_id)
        if sub and sub.get('status') == 'pending':
            result = await self.db.activate_subscription(track_id)
            if result:
                logger.info(f"✅ Subscription #{result['id']} activated for user {result['telegram_id']}")
                # Send Telegram notification
                await self._notify_user(
                    result['telegram_id'],
                    f"✅ <b>Subscription Activated!</b>\n\n"
                    f"💰 Amount: <b>${result['amount']:.2f}</b>\n"
                    f"📅 Valid until: <b>{result['expires_at'].strftime('%Y-%m-%d %H:%M')}</b>\n\n"
                    f"You now have full access to all features. 🚀"
                )
                return
        
        # 2. Otherwise check if it's a top-up payment
        confirmed = await self.db.confirm_payment(track_id, tx_hash)
        if confirmed:
            logger.info(f"✅ Top-up payment confirmed: {track_id}")
            # Get payment info to notify user
            try:
                async with self.db.pool.acquire() as conn:
                    payment = await conn.fetchrow("""
                        SELECT p.credits, u.telegram_id 
                        FROM payments p 
                        JOIN users u ON u.id = p.user_id 
                        WHERE p.track_id = $1
                    """, track_id)
                    if payment:
                        await self._notify_user(
                            payment['telegram_id'],
                            f"✅ <b>Payment Confirmed!</b>\n\n"
                            f"💰 <b>${payment['credits']:.2f}</b> credits added to your account.\n\n"
                            f"Thank you for your payment! 🎉"
                        )
            except Exception as e:
                logger.warning(f"Could not send payment notification: {e}")
        else:
            logger.warning(f"⚠️ Payment {track_id} not found or already confirmed")
    
    async def _notify_user(self, telegram_id: int, message: str):
        """Send a notification message to a user via Telegram"""
        if not self.bot_app:
            logger.warning("No bot_app set, cannot send notification")
            return
        try:
            await self.bot_app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"📤 Notification sent to {telegram_id}")
        except Exception as e:
            logger.error(f"❌ Failed to notify user {telegram_id}: {e}")
