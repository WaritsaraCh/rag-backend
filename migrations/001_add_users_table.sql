-- Migration: Add users table and update conversations table
-- Run this after the initial schema01.sql

-- 1. Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Store hashed passwords only
    full_name VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    metadata JSONB -- For additional user preferences/settings
);

-- 2. Create indexes for users table
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_created ON users(created_at DESC);
CREATE INDEX idx_users_metadata ON users USING GIN (metadata);

-- 3. Add foreign key constraint to conversations table
-- First, we need to handle existing data in conversations table
-- Update existing conversations to reference a default user (optional)
-- You can skip this if you want to keep existing conversations as-is

-- Option A: Create a default system user for existing conversations
INSERT INTO users (username, email, password_hash, full_name, is_admin) 
VALUES ('system', 'system@localhost', 'no_password', 'System User', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Option B: Update conversations table structure
-- First, add a new user_id_fk column as integer
ALTER TABLE conversations ADD COLUMN user_id_fk INTEGER;

-- Update existing conversations to reference the system user
UPDATE conversations 
SET user_id_fk = (SELECT id FROM users WHERE username = 'system' LIMIT 1)
WHERE user_id_fk IS NULL;

-- Add foreign key constraint
ALTER TABLE conversations 
ADD CONSTRAINT fk_conversations_user 
FOREIGN KEY (user_id_fk) REFERENCES users(id) ON DELETE SET NULL;

-- Create index for the new foreign key
CREATE INDEX idx_conversation_user ON conversations(user_id_fk);

-- 4. Optional: You can keep the old user_id column for backward compatibility
-- or drop it after migrating all data
-- ALTER TABLE conversations DROP COLUMN user_id;

-- 5. Create a function to update user's updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Create trigger to automatically update updated_at
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_updated_at();

-- 7. Create a view for user statistics (optional)
CREATE VIEW user_stats AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.full_name,
    u.created_at,
    u.last_login_at,
    COUNT(DISTINCT c.id) as conversation_count,
    COUNT(DISTINCT m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM users u
LEFT JOIN conversations c ON u.id = c.user_id_fk
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY u.id, u.username, u.email, u.full_name, u.created_at, u.last_login_at;