# =============================================================================
# Oxapay Payment Handler
# =============================================================================
# Integration with Oxapay cryptocurrency payment gateway
# =============================================================================

import aiohttp
import logging
import uuid
from typing import Dict, Optional

from config import OXAPAY_API_KEY, OXAPAY_API_URL, OXAPAY_WEBHOOK_URL

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
        """Create payment invoice with Oxapay"""
        if not order_id:
            order_id = str(uuid.uuid4())
        
        headers = {
            "Content-Type": "application/json",
            "merchant": self.api_key,
        }
        
        payload = {
            "amount": amount,
            "currency": currency,
            "orderId": order_id,
            "callbackUrl": self.webhook_url,
            "description": description or f"SIP Credit Top-up ${amount}",
            "returnUrl": "https://t.me/callnowp1_bot",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"Oxapay request: url={self.api_url}, payload={payload}")
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.info(f"Oxapay raw response: status={response.status}, body={response_text[:500]}")
                    
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}: {response_text[:200]}"
                        }
                    
                    try:
                        data = await response.json(content_type=None)
                    except Exception as json_err:
                        return {
                            'success': False,
                            'error': f"JSON parse error: {str(json_err)[:100]}, body: {response_text[:200]}"
                        }
                    
                    if data.get('result') == 100:
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
                        error_msg = data.get('message', f"Unknown error: {data}")
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
        """Verify webhook authenticity"""
        return True


# Global instance
oxapay = OxapayHandler()
