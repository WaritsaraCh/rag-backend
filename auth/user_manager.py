"""
User management utilities for the RAG project.
Provides functions to create, authenticate, and manage users.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from database.operations import get_conn, release_conn
from psycopg2.extras import RealDictCursor
import psycopg2

class UserManager:
    """Handles user operations for the RAG system"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash"""
        try:
            salt, hash_part = stored_hash.split(':')
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return password_hash == hash_part
        except ValueError:
            return False
    
    @staticmethod
    def create_user(username: str, email: str, password: str, 
                   full_name: Optional[str] = None, 
                   is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if user already exists
                cur.execute(
                    "SELECT id FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
                if cur.fetchone():
                    return None  # User already exists
                
                # Hash password
                password_hash = UserManager.hash_password(password)
                
                # Insert new user
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, full_name, is_admin)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, username, email, full_name, is_admin, created_at
                """, (username, email, password_hash, full_name, is_admin))
                
                user = cur.fetchone()
                conn.commit()
                return dict(user) if user else None
                
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error creating user: {e}")
            return None
        finally:
            release_conn(conn)
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user by username/email and password"""
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Find user by username or email
                cur.execute("""
                    SELECT id, username, email, password_hash, full_name, 
                           is_admin, is_active, last_login_at
                    FROM users 
                    WHERE (username = %s OR email = %s) AND is_active = TRUE
                """, (username, username))
                
                user = cur.fetchone()
                if not user:
                    return None
                
                # Verify password
                if not UserManager.verify_password(password, user['password_hash']):
                    return None
                
                # Update last login
                cur.execute(
                    "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )
                conn.commit()
                
                # Return user data (without password hash)
                user_data = dict(user)
                del user_data['password_hash']
                return user_data
                
        except psycopg2.Error as e:
            print(f"Error authenticating user: {e}")
            return None
        finally:
            release_conn(conn)
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, username, email, full_name, avatar_url,
                           is_admin, is_active, created_at, last_login_at, metadata
                    FROM users 
                    WHERE id = %s AND is_active = TRUE
                """, (user_id,))
                
                user = cur.fetchone()
                return dict(user) if user else None
                
        except psycopg2.Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            release_conn(conn)
    
    @staticmethod
    def update_user_profile(user_id: int, **kwargs) -> bool:
        """Update user profile fields"""
        allowed_fields = ['full_name', 'avatar_url', 'metadata']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # Build dynamic update query
                set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
                values = list(updates.values()) + [user_id]
                
                cur.execute(f"""
                    UPDATE users 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND is_active = TRUE
                """, values)
                
                conn.commit()
                return cur.rowcount > 0
                
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating user: {e}")
            return False
        finally:
            release_conn(conn)
    
    @staticmethod
    def get_user_conversations(user_id: int, limit: int = 50) -> list:
        """Get user's conversation history"""
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT c.id, c.session_id, c.created_at, c.metadata,
                           COUNT(m.id) as message_count,
                           MAX(m.created_at) as last_message_at
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.user_id_fk = %s
                    GROUP BY c.id, c.session_id, c.created_at, c.metadata
                    ORDER BY c.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return [dict(row) for row in cur.fetchall()]
                
        except psycopg2.Error as e:
            print(f"Error getting user conversations: {e}")
            return []
        finally:
            release_conn(conn)

# Convenience functions
def create_user(username: str, email: str, password: str, **kwargs):
    """Create a new user (convenience function)"""
    return UserManager.create_user(username, email, password, **kwargs)

def authenticate(username: str, password: str):
    """Authenticate user (convenience function)"""
    return UserManager.authenticate_user(username, password)

def get_user(user_id: int):
    """Get user by ID (convenience function)"""
    return UserManager.get_user_by_id(user_id)