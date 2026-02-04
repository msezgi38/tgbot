# =============================================================================
# Oxapay Payment Handler
# =============================================================================
# Integration with Oxapay cryptocurrency payment gateway
# =============================================================================

import aiohttp
import logging
import hashlib
import uuid
from typing import Dict, Optional
from datetime import datetime

from config import OXAPAY_API_KEY, OXAPAY_API_URL, OXAPAY_WEBHOOK_URL, CREDIT_PACKAGES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OxapayHandler:
    """Oxapay payment gateway integration"""
    
    def __init__(self):
        self.api_key = OXAPAY_API_KEY
        self.api_url = OXAPAY_API_URL
        self.webhook_url = OXAPAY_WEBHOOK_URL
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "USDT",
        order_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict:
        """
        Create payment request with Oxapay
        
        Returns:
            {
                'success': bool,
                'track_id': str,
                'payment_url': str,
                'amount': float,
                'error': str (if failed)
            }
        """
        if not order_id:
            order_id = str(uuid.uuid4())
        
        payload = {
            "merchant": self.api_key,
            "amount": amount,
            "currency": currency,
            "orderId": order_id,
            "callbackUrl": self.webhook_url,
            "description": description or "IVR Bot Credits",
            "returnUrl": "https://t.me/your_bot_username",  # ⚠️ Update with your bot
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get('result') == 100:
                        # Success
                        result = {
                            'success': True,
                            'track_id': data.get('trackId'),
                            'payment_url': data.get('payLink'),
                            'amount': amount,
                            'currency': currency,
                            'order_id': order_id
                        }
                        
                        logger.info(f"✅ Payment created: {result['track_id']}")
                        return result
                    else:
                        # Error
                        error_msg = data.get('message', 'Unknown error')
                        logger.error(f"❌ Oxapay error: {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg
                        }
                        
        except Exception as e:
            logger.error(f"❌ Exception creating payment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_webhook(self, data: Dict) -> bool:
        """
        Verify webhook authenticity
        
        Oxapay sends a signature to verify the webhook is genuine
        """
        # Oxapay verification logic here
        # Check their documentation for exact verification method
        return True  # Simplified for now
    
    def get_credit_package(self, package_id: str) -> Optional[Dict]:
        """Get credit package details"""
        return CREDIT_PACKAGES.get(package_id)
    
    def list_packages(self) -> Dict:
        """Get all available credit packages"""
        return CREDIT_PACKAGES


# Global instance
oxapay = OxapayHandler()


# =============================================================================
# Example Usage
# =============================================================================
async def test_payment():
    """Test payment creation"""
    handler = OxapayHandler()
    
    result = await handler.create_payment(
        amount=5.00,
        currency="USDT",
        description="10 credits"
    )
    
    if result['success']:
        print(f"Payment URL: {result['payment_url']}")
        print(f"Track ID: {result['track_id']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_payment())
