# =============================================================================
# Mock Database for UI Testing
# =============================================================================
# Dummy data version - No PostgreSQL required
# =============================================================================

from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockDatabase:
    """Mock database with sample data for UI testing"""
    
    def __init__(self):
        self.connected = False
        # Mock data storage
        self.users = {}
        self.campaigns = {}
        self.next_campaign_id = 1
        
        # Voice files storage - saved uploaded voice files
        self.voice_files = {
            1: {
                'id': 1,
                'name': 'Product Intro Voice',
                'duration': 45,
                'uploaded_at': datetime.now() - timedelta(days=5)
            },
            2: {
                'id': 2,
                'name': 'Survey Questions',
                'duration': 32,
                'uploaded_at': datetime.now() - timedelta(days=2)
            },
            3: {
                'id': 3,
                'name': 'Event Invitation',
                'duration': 28,
                'uploaded_at': datetime.now() - timedelta(hours=12)
            }
        }
        self.next_voice_id = 4
        
        # Preset Caller IDs - Verified, high-performance numbers
        self.preset_cids = [
            {'id': 1, 'number': '18889092337', 'name': 'Premium CID #1', 'verified': True},
            {'id': 2, 'number': '18552847621', 'name': 'Premium CID #2', 'verified': True},
            {'id': 3, 'number': '18667123456', 'name': 'Premium CID #3', 'verified': True},
            {'id': 4, 'number': '18778901234', 'name': 'Premium CID #4', 'verified': True},
        ]
        
    async def connect(self):
        """Simulate database connection"""
        self.connected = True
        logger.info("✅ Mock Database connected (UI Test Mode)")
        return True
    
    async def close(self):
        """Simulate database close"""
        self.connected = False
        logger.info("Mock Database disconnected")
    
    # =========================================================================
    # User Operations
    # =========================================================================
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict:
        """Get or create mock user"""
        if telegram_id not in self.users:
            # Create new user with 1337 default settings
            self.users[telegram_id] = {
                'id': len(self.users) + 1,
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name or 'Test User',
                'last_name': last_name,
                # Balance & Credits
                'balance': 22.60,  # Current balance in dollars
                'credits': 22.60,  # Alias for compatibility
                'total_spent': 234.50,
                'total_calls': 567,
                # Caller ID Settings
                'caller_id': '18889092337',  # Default caller ID
                'country_code': '+1',  # US default
                # System Info
                'available_lines': 112,  # System capacity
                'lines_used': 437,  # Total lifetime usage
                'system_status': 'Ready',  # Ready, Maintenance, etc.
                # Account Status
                'is_active': True,
                'created_at': datetime.now() - timedelta(days=30),
                'last_active': datetime.now()
            }
            logger.info(f"👤 Mock user created: {telegram_id} ({username})")
        
        return self.users[telegram_id]
    
    async def get_user_credits(self, telegram_id: int) -> float:
        """Get user credits"""
        user = await self.get_or_create_user(telegram_id)
        return user['credits']
    
    async def add_credits(self, telegram_id: int, amount: float) -> float:
        """Add credits to user"""
        user = await self.get_or_create_user(telegram_id)
        user['credits'] += amount
        return user['credits']
    
    # =========================================================================
    # Campaign Operations
    # =========================================================================
    
    async def create_campaign(
        self,
        user_id: int,
        name: str,
        caller_id: Optional[str] = None
    ) -> int:
        """Create mock campaign"""
        campaign_id = self.next_campaign_id
        self.next_campaign_id += 1
        
        self.campaigns[campaign_id] = {
            'id': campaign_id,
            'user_id': user_id,
            'name': name,
            'caller_id': caller_id,
            'total_numbers': 0,
            'completed': 0,
            'answered': 0,
            'pressed_one': 0,
            'failed': 0,
            'status': 'draft',
            'estimated_cost': 0.00,
            'actual_cost': 0.00,
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None
        }
        
        return campaign_id
    
    async def add_campaign_numbers(self, campaign_id: int, phone_numbers: List[str]) -> int:
        """Add numbers to campaign"""
        if campaign_id in self.campaigns:
            count = len(phone_numbers)
            self.campaigns[campaign_id]['total_numbers'] = count
            self.campaigns[campaign_id]['estimated_cost'] = count * 1.0
        return len(phone_numbers)
    
    async def start_campaign(self, campaign_id: int) -> bool:
        """Start campaign"""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]['status'] = 'running'
            self.campaigns[campaign_id]['started_at'] = datetime.now()
        return True
    
    async def stop_campaign(self, campaign_id: int) -> bool:
        """Pause campaign"""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]['status'] = 'paused'
        return True
    
    async def get_campaign_stats(self, campaign_id: int) -> Dict:
        """Get campaign statistics"""
        if campaign_id in self.campaigns:
            return self.campaigns[campaign_id]
        return {}
    
    async def get_user_campaigns(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user campaigns with mock data"""
        # Create some sample campaigns for demo
        sample_campaigns = [
            {
                'id': 1,
                'name': 'Product Launch 2026',
                'total_numbers': 100,
                'completed': 85,
                'pressed_one': 28,
                'status': 'running',
                'actual_cost': 14.50,
                'created_at': datetime.now() - timedelta(hours=2)
            },
            {
                'id': 2,
                'name': 'Lead Generation Q1',
                'total_numbers': 250,
                'completed': 250,
                'pressed_one': 67,
                'status': 'completed',
                'actual_cost': 42.30,
                'created_at': datetime.now() - timedelta(days=3)
            },
            {
                'id': 3,
                'name': 'Customer Survey',
                'total_numbers': 50,
                'completed': 12,
                'pressed_one': 4,
                'status': 'paused',
                'actual_cost': 2.80,
                'created_at': datetime.now() - timedelta(days=1)
            },
            {
                'id': 4,
                'name': 'Event Invitation',
                'total_numbers': 150,
                'completed': 0,
                'pressed_one': 0,
                'status': 'draft',
                'actual_cost': 0.00,
                'created_at': datetime.now() - timedelta(hours=6)
            }
        ]
        
        # Add any real campaigns created during testing
        for campaign in self.campaigns.values():
            if campaign['user_id'] == user_id:
                sample_campaigns.append(campaign)
        
        return sample_campaigns[:limit]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    async def get_user_stats(self, telegram_id: int) -> Dict:
        """Get user statistics"""
        user = await self.get_or_create_user(telegram_id)
        
        return {
            'credits': user['credits'],
            'total_spent': user['total_spent'],
            'total_calls': user['total_calls'],
            'created_at': user['created_at'],
            'campaign_count': 4  # Mock campaign count
        }
    
    # =========================================================================
    # Payment Operations (Mock)
    # =========================================================================
    
    async def create_payment(
        self,
        user_id: int,
        track_id: str,
        amount: float,
        credits: float,
        currency: str = "USDT",
        payment_url: str = None
    ) -> int:
        """Create mock payment"""
        logger.info(f"💳 Mock payment created: {credits} credits for ${amount}")
        return 1
    
    async def confirm_payment(self, track_id: str, tx_hash: Optional[str] = None) -> bool:
        """Mock payment confirmation"""
        logger.info(f"✅ Mock payment confirmed: {track_id}")
        return True
    
    # =========================================================================
    # Voice Files Management
    # =========================================================================
    
    async def get_user_voice_files(self, user_id: int) -> List[Dict]:
        """Get all saved voice files for a user"""
        # For mock, return all voice files
        return list(self.voice_files.values())
    
    async def save_voice_file(self, user_id: int, name: str, duration: int = 30) -> int:
        """Save a new voice file"""
        voice_id = self.next_voice_id
        self.next_voice_id += 1
        
        self.voice_files[voice_id] = {
            'id': voice_id,
            'name': name,
            'duration': duration,
            'uploaded_at': datetime.now()
        }
        
        logger.info(f"🎤 Voice file saved: {name}")
        return voice_id
    
    async def get_voice_file(self, voice_id: int) -> Dict:
        """Get a specific voice file"""
        return self.voice_files.get(voice_id, {})
    
    # =========================================================================
    # Caller ID Management
    # =========================================================================
    
    async def get_preset_cids(self) -> List[Dict]:
        """Get list of preset verified caller IDs"""
        return self.preset_cids
    
    async def set_caller_id(self, telegram_id: int, caller_id: str) -> bool:
        """Set user's caller ID"""
        user = await self.get_or_create_user(telegram_id)
        user['caller_id'] = caller_id
        logger.info(f"📞 Caller ID set: {caller_id} for user {telegram_id}")
        return True
    
    async def get_caller_id(self, telegram_id: int) -> str:
        """Get user's current caller ID"""
        user = await self.get_or_create_user(telegram_id)
        return user.get('caller_id', '18889092337')
    
    async def validate_cid(self, cid: str) -> tuple[bool, str]:
        """Validate caller ID format and check blacklist"""
        # Remove any non-digits
        clean_cid = ''.join(filter(str.isdigit, cid))
        
        # Check length
        if len(clean_cid) < 10 or len(clean_cid) > 15:
            return False, "CID must be 10-15 digits"
        
        # Mock blacklist check (in real system, check against actual blacklist)
        blacklisted = ['15551234567', '18005551234']  # Mock bad numbers
        if clean_cid in blacklisted:
            return False, "This number is blacklisted"
        
        return True, "CID validated successfully"
    
    # =========================================================================
    # Balance Management
    # =========================================================================
    
    async def get_balance(self, telegram_id: int) -> float:
        """Get user's current balance"""
        user = await self.get_or_create_user(telegram_id)
        return user.get('balance', 0.0)
    
    async def add_balance(self, telegram_id: int, amount: float) -> float:
        """Add credits to user balance"""
        user = await self.get_or_create_user(telegram_id)
        user['balance'] += amount
        logger.info(f"💰 Added ${amount:.2f} to user {telegram_id}. New balance: ${user['balance']:.2f}")
        return user['balance']
    
    async def deduct_balance(self, telegram_id: int, amount: float) -> bool:
        """Deduct credits from user balance"""
        user = await self.get_or_create_user(telegram_id)
        if user['balance'] >= amount:
            user['balance'] -= amount
            logger.info(f"💸 Deducted ${amount:.2f} from user {telegram_id}. Remaining: ${user['balance']:.2f}")
            return True
        return False
    
    # =========================================================================
    # Call Logs - Detailed Results
    # =========================================================================
    
    async def get_campaign_call_logs(self, campaign_id: int, limit: int = 50) -> List[Dict]:
        """Get detailed call logs for a campaign"""
        # Mock detailed call logs
        sample_logs = [
            {
                'phone_number': '+1234567890',
                'status': 'pressed_one',
                'answered': True,
                'pressed_one': True,
                'duration': 45,
                'cost': 0.75,
                'timestamp': datetime.now() - timedelta(minutes=5)
            },
            {
                'phone_number': '+1234567891',
                'status': 'answered',
                'answered': True,
                'pressed_one': False,
                'duration': 30,
                'cost': 0.50,
                'timestamp': datetime.now() - timedelta(minutes=10)
            },
            {
                'phone_number': '+1234567892',
                'status': 'pressed_one',
                'answered': True,
                'pressed_one': True,
                'duration': 52,
                'cost': 0.87,
                'timestamp': datetime.now() - timedelta(minutes=15)
            },
            {
                'phone_number': '+1234567893',
                'status': 'no_answer',
                'answered': False,
                'pressed_one': False,
                'duration': 0,
                'cost': 0.10,
                'timestamp': datetime.now() - timedelta(minutes=18)
            },
            {
                'phone_number': '+1234567894',
                'status': 'pressed_one',
                'answered': True,
                'pressed_one': True,
                'duration': 38,
                'cost': 0.63,
                'timestamp': datetime.now() - timedelta(minutes=22)
            },
            {
                'phone_number': '+1234567895',
                'status': 'failed',
                'answered': False,
                'pressed_one': False,
                'duration': 0,
                'cost': 0.05,
                'timestamp': datetime.now() - timedelta(minutes=25)
            },
            {
                'phone_number': '+1234567896',
                'status': 'answered',
                'answered': True,
                'pressed_one': False,
                'duration': 28,
                'cost': 0.47,
                'timestamp': datetime.now() - timedelta(minutes=28)
            },
            {
                'phone_number': '+1234567897',
                'status': 'pressed_one',
                'answered': True,
                'pressed_one': True,
                'duration': 41,
                'cost': 0.68,
                'timestamp': datetime.now() - timedelta(minutes=30)
            },
            {
                'phone_number': '+1234567898',
                'status': 'no_answer',
                'answered': False,
                'pressed_one': False,
                'duration': 0,
                'cost': 0.10,
                'timestamp': datetime.now() - timedelta(minutes=33)
            },
            {
                'phone_number': '+1234567899',
                'status': 'answered',
                'answered': True,
                'pressed_one': False,
                'duration': 25,
                'cost': 0.42,
                'timestamp': datetime.now() - timedelta(minutes=35)
            },
        ]
        
        return sample_logs[:limit]


# Global mock database instance
db = MockDatabase()
