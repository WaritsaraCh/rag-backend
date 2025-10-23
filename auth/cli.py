#!/usr/bin/env python3
"""
User management CLI tool for the RAG project.
Provides commands to create, list, and manage users.
"""

import sys
import argparse
from getpass import getpass
from auth.user_manager import UserManager

def create_user_command(args):
    """Create a new user"""
    username = args.username or input("Username: ")
    email = args.email or input("Email: ")
    
    if args.password:
        password = args.password
    else:
        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")
        if password != confirm_password:
            print("❌ Passwords don't match!")
            return False
    
    full_name = args.full_name or input("Full name (optional): ") or None
    is_admin = args.admin
    
    print(f"\n🔄 Creating user '{username}'...")
    
    user = UserManager.create_user(
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        is_admin=is_admin
    )
    
    if user:
        print("✅ User created successfully!")
        print(f"   ID: {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   Full name: {user['full_name'] or 'Not set'}")
        print(f"   Admin: {'Yes' if user['is_admin'] else 'No'}")
        print(f"   Created: {user['created_at']}")
        return True
    else:
        print("❌ Failed to create user (username or email might already exist)")
        return False

def list_users_command(args):
    """List all users"""
    from database.operations import get_conn, release_conn
    from psycopg2.extras import RealDictCursor
    
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.id, u.username, u.email, u.full_name, u.is_admin, 
                       u.is_active, u.created_at, u.last_login_at,
                       COUNT(DISTINCT c.id) as conversation_count,
                       COUNT(DISTINCT m.id) as message_count
                FROM users u
                LEFT JOIN conversations c ON u.id = c.user_id_fk
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY u.id, u.username, u.email, u.full_name, u.is_admin, 
                         u.is_active, u.created_at, u.last_login_at
                ORDER BY u.created_at DESC
            """)
            
            users = cur.fetchall()
            
            if not users:
                print("📭 No users found")
                return
            
            print(f"\n👥 Found {len(users)} users:")
            print("=" * 80)
            
            for user in users:
                status = "🟢 Active" if user['is_active'] else "🔴 Inactive"
                admin_badge = " 👑 Admin" if user['is_admin'] else ""
                
                print(f"ID: {user['id']:<3} | {user['username']:<15} | {status}{admin_badge}")
                print(f"      Email: {user['email']}")
                print(f"      Name: {user['full_name'] or 'Not set'}")
                print(f"      Created: {user['created_at']}")
                print(f"      Last login: {user['last_login_at'] or 'Never'}")
                print(f"      Conversations: {user['conversation_count']}, Messages: {user['message_count']}")
                print("-" * 80)
                
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    finally:
        release_conn(conn)

def test_auth_command(args):
    """Test user authentication"""
    username = args.username or input("Username/Email: ")
    password = args.password or getpass("Password: ")
    
    print(f"\n🔐 Testing authentication for '{username}'...")
    
    user = UserManager.authenticate_user(username, password)
    
    if user:
        print("✅ Authentication successful!")
        print(f"   ID: {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   Full name: {user['full_name'] or 'Not set'}")
        print(f"   Admin: {'Yes' if user['is_admin'] else 'No'}")
        print(f"   Last login: {user['last_login_at']}")
        return True
    else:
        print("❌ Authentication failed (invalid credentials or inactive user)")
        return False

def main():
    parser = argparse.ArgumentParser(description="RAG Project User Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create user command
    create_parser = subparsers.add_parser('create', help='Create a new user')
    create_parser.add_argument('--username', help='Username')
    create_parser.add_argument('--email', help='Email address')
    create_parser.add_argument('--password', help='Password (will prompt if not provided)')
    create_parser.add_argument('--full-name', help='Full name')
    create_parser.add_argument('--admin', action='store_true', help='Make user an admin')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List all users')
    
    # Test auth command
    auth_parser = subparsers.add_parser('auth', help='Test user authentication')
    auth_parser.add_argument('--username', help='Username or email')
    auth_parser.add_argument('--password', help='Password (will prompt if not provided)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🚀 RAG Project - User Management")
    print("=" * 40)
    
    try:
        if args.command == 'create':
            create_user_command(args)
        elif args.command == 'list':
            list_users_command(args)
        elif args.command == 'auth':
            test_auth_command(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()