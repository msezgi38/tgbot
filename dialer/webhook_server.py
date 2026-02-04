# =============================================================================
# DTMF Webhook Server
# =============================================================================
# FastAPI server that receives DTMF events from Asterisk dialplan
# Updates database and notifies campaign worker
# =============================================================================

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncpg
from datetime import datetime

from config import DATABASE_URL, WEBHOOK_HOST, WEBHOOK_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IVR Bot Webhook Server")

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


# =============================================================================
# Request Models
# =============================================================================
class DTMFWebhookRequest(BaseModel):
    call_id: str
    destination: str
    dtmf_pressed: int  # 0 or 1
    callerid: Optional[str] = None
    hangup_cause: Optional[str] = None
    duration: Optional[int] = 0


# =============================================================================
# Database Functions
# =============================================================================
async def init_db():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        logger.info("✅ Database connection pool created")
    except Exception as e:
        logger.error(f"❌ Failed to create database pool: {e}")


async def close_db():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")


async def update_call_record(
    call_id: str,
    dtmf_pressed: int,
    hangup_cause: Optional[str] = None,
    duration: int = 0
):
    """Update call record in database"""
    if not db_pool:
        logger.error("Database pool not initialized")
        return False
    
    try:
        async with db_pool.acquire() as conn:
            # Calculate cost based on duration
            cost = calculate_cost(duration)
            
            # Update call record
            await conn.execute("""
                UPDATE calls
                SET dtmf_pressed = $1,
                    hangup_cause = $2,
                    billsec = $3,
                    cost = $4,
                    ended_at = $5,
                    status = $6
                WHERE call_id = $7
            """, dtmf_pressed, hangup_cause, duration, cost, datetime.now(),
                'ANSWERED' if dtmf_pressed else 'NO_DTMF', call_id)
            
            # Update campaign statistics
            await conn.execute("""
                UPDATE campaigns
                SET completed = completed + 1,
                    pressed_one = pressed_one + $1,
                    actual_cost = actual_cost + $2
                WHERE id = (SELECT campaign_id FROM calls WHERE call_id = $3)
            """, dtmf_pressed, cost, call_id)
            
            # Update campaign_data status
            await conn.execute("""
                UPDATE campaign_data
                SET status = 'completed'
                WHERE call_id = $1
            """, call_id)
            
            # Deduct credits from user
            await conn.execute("""
                UPDATE users
                SET credits = credits - $1,
                    total_spent = total_spent + $1
                WHERE id = (
                    SELECT user_id FROM campaigns
                    WHERE id = (SELECT campaign_id FROM calls WHERE call_id = $2)
                )
            """, cost, call_id)
            
            logger.info(f"✅ Updated call {call_id}: DTMF={dtmf_pressed}, Cost={cost}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error updating call record: {e}")
        return False


def calculate_cost(duration_seconds: int) -> float:
    """
    Calculate call cost based on duration
    Uses 6-second billing increments (standard telecom billing)
    """
    from config import COST_PER_MINUTE, BILLING_INCREMENT_SECONDS, MINIMUM_BILLABLE_SECONDS
    
    if duration_seconds < MINIMUM_BILLABLE_SECONDS:
        billable_seconds = MINIMUM_BILLABLE_SECONDS
    else:
        # Round up to nearest billing increment
        billable_seconds = (
            (duration_seconds + BILLING_INCREMENT_SECONDS - 1) // BILLING_INCREMENT_SECONDS
        ) * BILLING_INCREMENT_SECONDS
    
    # Convert to minutes and calculate cost
    billable_minutes = billable_seconds / 60.0
    cost = billable_minutes * COST_PER_MINUTE
    
    return round(cost, 4)


# =============================================================================
# API Endpoints
# =============================================================================
@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    await init_db()
    logger.info("🚀 Webhook server started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await close_db()
    logger.info("🛑 Webhook server stopped")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "IVR Bot Webhook Server",
        "status": "running",
        "version": "1.0"
    }


@app.post("/dtmf_webhook")
async def dtmf_webhook(
    request: DTMFWebhookRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive DTMF webhook from Asterisk dialplan
    
    Called when:
    - User presses '1' (dtmf_pressed = 1)
    - No response/timeout (dtmf_pressed = 0)
    - Call ends unexpectedly (hangup_cause provided)
    """
    logger.info(f"📨 Webhook received: {request.dict()}")
    
    # Validate call_id exists
    if not request.call_id:
        raise HTTPException(status_code=400, detail="call_id is required")
    
    # Update database in background
    background_tasks.add_task(
        update_call_record,
        request.call_id,
        request.dtmf_pressed,
        request.hangup_cause,
        request.duration or 0
    )
    
    return {
        "status": "success",
        "message": "Webhook processed",
        "call_id": request.call_id,
        "dtmf_pressed": request.dtmf_pressed
    }


@app.get("/stats")
async def get_stats():
    """Get overall system statistics"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_pool.acquire() as conn:
            # Get total users
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Get total campaigns
            total_campaigns = await conn.fetchval("SELECT COUNT(*) FROM campaigns")
            
            # Get total calls
            total_calls = await conn.fetchval("SELECT COUNT(*) FROM calls")
            
            # Get success rate
            successful_calls = await conn.fetchval(
                "SELECT COUNT(*) FROM calls WHERE dtmf_pressed = 1"
            )
            
            success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
            
            return {
                "total_users": total_users,
                "total_campaigns": total_campaigns,
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "success_rate": f"{success_rate:.2f}%"
            }
            
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Run Server
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=WEBHOOK_HOST,
        port=WEBHOOK_PORT,
        log_level="info"
    )
