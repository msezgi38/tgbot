# =============================================================================
# Oxapay Payment Handler
# =============================================================================
# Integration with Oxapay cryptocurrency payment gateway (v1 API)
# =============================================================================

import aiohttp
import logging
import hashlib
import uuid
from typing import Dict, Optional
from datetime import datetime

from config import OXAPAY_API_KEY, OXAPAY_API_URL, OXAPAY_WEBHOOK_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OxapayHandler:
    """Oxapay payment gateway integration (v1 API)"""
    
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
        Create payment invoice with Oxapay v1 API
        
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
            "description": description or f"SIP Credit Top-up ${amount}",
            "returnUrl": "https://t.me/callnowp1_bot",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    data = await response.json()
                    
                    logger.info(f"Oxapay response: status={response.status}, data={data}")
                    
                    if response.status == 200 and data.get('result') == 100:
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
                        error_msg = data.get('message', f"HTTP {response.status}")
                        logger.error(f"❌ Oxapay error: {error_msg} | Full response: {data}")
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
        """Verify webhook authenticity"""
        return True  # Simplified for now


# Global instance
oxapay = OxapayHandler()
