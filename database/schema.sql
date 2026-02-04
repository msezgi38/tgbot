-- =============================================================================
-- PostgreSQL Database Schema for Press-1 IVR Bot
-- =============================================================================
-- This schema supports:
-- 1. User management and credit tracking
-- 2. Campaign management
-- 3. Call detail records (CDR)
-- 4. Payment processing via Oxapay
-- =============================================================================

-- Drop existing tables if re-creating
DROP TABLE IF EXISTS calls CASCADE;
DROP TABLE IF EXISTS campaign_data CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- =============================================================================
-- Users Table
-- =============================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,              -- Telegram user ID
    username VARCHAR(255),                            -- Telegram username
    first_name VARCHAR(255),                          -- Telegram first name
    last_name VARCHAR(255),                           -- Telegram last name
    credits DECIMAL(10, 2) DEFAULT 0.00,              -- Available credits/minutes
    total_spent DECIMAL(10, 2) DEFAULT 0.00,          -- Lifetime spending
    total_calls INTEGER DEFAULT 0,                    -- Total calls made
    is_active BOOLEAN DEFAULT TRUE,                   -- Account status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- =============================================================================
-- Payments Table (Oxapay)
-- =============================================================================
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    track_id VARCHAR(255) UNIQUE,                     -- Oxapay track ID
    order_id VARCHAR(255),                            -- Our internal order ID
    amount DECIMAL(10, 2) NOT NULL,                   -- Payment amount
    currency VARCHAR(10) DEFAULT 'USDT',              -- Cryptocurrency
    credits DECIMAL(10, 2),                           -- Credits to add
    status VARCHAR(50) DEFAULT 'pending',             -- pending, paid, confirmed, failed
    payment_url TEXT,                                 -- Oxapay payment link
    tx_hash VARCHAR(255),                             -- Blockchain transaction hash
    callback_data JSONB,                              -- Raw webhook data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    confirmed_at TIMESTAMP
);

CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_track_id ON payments(track_id);
CREATE INDEX idx_payments_status ON payments(status);

-- =============================================================================
-- Campaigns Table
-- =============================================================================
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,                       -- Campaign name
    caller_id VARCHAR(50),                            -- CallerID to use
    total_numbers INTEGER DEFAULT 0,                  -- Total phone numbers
    completed INTEGER DEFAULT 0,                      -- Calls completed
    answered INTEGER DEFAULT 0,                       -- Calls answered
    pressed_one INTEGER DEFAULT 0,                    -- Successful press-1
    failed INTEGER DEFAULT 0,                         -- Failed calls
    status VARCHAR(50) DEFAULT 'draft',               -- draft, running, paused, completed
    estimated_cost DECIMAL(10, 2),                    -- Estimated credit cost
    actual_cost DECIMAL(10, 2) DEFAULT 0.00,          -- Actual cost so far
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- =============================================================================
-- Campaign Data Table (Phone Numbers)
-- =============================================================================
CREATE TABLE campaign_data (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    phone_number VARCHAR(50) NOT NULL,                -- Destination number
    status VARCHAR(50) DEFAULT 'pending',             -- pending, dialing, answered, failed, completed
    call_id VARCHAR(255),                             -- Asterisk unique call ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    called_at TIMESTAMP
);

CREATE INDEX idx_campaign_data_campaign_id ON campaign_data(campaign_id);
CREATE INDEX idx_campaign_data_status ON campaign_data(status);
CREATE INDEX idx_campaign_data_call_id ON campaign_data(call_id);

-- =============================================================================
-- Calls Table (Call Detail Records)
-- =============================================================================
CREATE TABLE calls (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    campaign_data_id INTEGER REFERENCES campaign_data(id) ON DELETE CASCADE,
    call_id VARCHAR(255) UNIQUE,                      -- Asterisk unique call ID
    phone_number VARCHAR(50) NOT NULL,                -- Destination
    caller_id VARCHAR(50),                            -- CallerID used
    status VARCHAR(50),                               -- ANSWER, BUSY, NO ANSWER, FAILED
    dtmf_pressed INTEGER DEFAULT 0,                   -- 1 if pressed, 0 if not
    duration INTEGER DEFAULT 0,                       -- Total call duration (seconds)
    billsec INTEGER DEFAULT 0,                        -- Billable duration (seconds)
    cost DECIMAL(10, 4) DEFAULT 0.0000,               -- Cost in credits
    hangup_cause VARCHAR(100),                        -- Asterisk hangup cause
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    answered_at TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE INDEX idx_calls_campaign_id ON calls(campaign_id);
CREATE INDEX idx_calls_call_id ON calls(call_id);
CREATE INDEX idx_calls_status ON calls(status);

-- =============================================================================
-- Sample Data (Optional - for testing)
-- =============================================================================

-- Create a test user
INSERT INTO users (telegram_id, username, first_name, credits) 
VALUES (123456789, 'testuser', 'Test', 100.00);

-- =============================================================================
-- Useful Queries
-- =============================================================================

-- Check user balance
-- SELECT username, credits, total_calls FROM users WHERE telegram_id = 123456789;

-- Get campaign statistics
-- SELECT 
--     c.name,
--     c.total_numbers,
--     c.completed,
--     c.pressed_one,
--     c.actual_cost,
--     c.status
-- FROM campaigns c
-- WHERE c.user_id = 1;

-- Get call details for a campaign
-- SELECT 
--     call_id,
--     phone_number,
--     status,
--     dtmf_pressed,
--     billsec,
--     cost
-- FROM calls
-- WHERE campaign_id = 1
-- ORDER BY started_at DESC;

-- =============================================================================
