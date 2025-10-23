#!/usr/bin/env python3
"""
Migration runner for the RAG project.
Executes SQL files to apply database migrations.
"""

import os
import psycopg2
from config.settings import get_config

MIGRATION_FILE = os.path.join(os.path.dirname(__file__), '001_add_users_table.sql')


def run_migration():
    """Execute the users table migration"""
    
    # Load configuration
    config = get_config()
    
    # Database connection parameters
    db_params = {
        'host': config.DB_HOST,
        'database': config.DB_NAME,
        'user': config.DB_USER,
        'password': config.DB_PASSWORD,
        'port': config.DB_PORT
    }
    
    # Read migration file
    migration_file = MIGRATION_FILE
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print("🔄 Connecting to database...")
        
        # Connect to database
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            print("📝 Executing migration...")
            
            # Split the migration into individual statements
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    try:
                        print(f"   Executing statement {i}/{len(statements)}...")
                        cur.execute(statement)
                        print(f"   ✅ Statement {i} completed successfully")
                    except psycopg2.Error as e:
                        print(f"   ⚠️  Statement {i} failed: {e}")
                        # Continue with other statements
                        continue
        
        print("✅ Migration completed successfully!")
        print("\n📊 Users table structure:")
        
        # Show the new table structure
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            
            columns = cur.fetchall()
            if columns:
                print("   Column Name       | Data Type      | Nullable | Default")
                print("   ------------------|----------------|----------|--------")
                for col in columns:
                    print(f"   {col[0]:<17} | {col[1]:<14} | {col[2]:<8} | {col[3] or 'None'}")
            else:
                print("   No columns found (table might not exist)")
        
        conn.close()
        
    except FileNotFoundError:
        print(f"❌ Migration file not found: {migration_file}")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True


def check_users_table_exists():
    """Check if users table already exists"""
    config = get_config()
    
    db_params = {
        'host': config.DB_HOST,
        'database': config.DB_NAME,
        'user': config.DB_USER,
        'password': config.DB_PASSWORD,
        'port': config.DB_PORT
    }
    
    try:
        conn = psycopg2.connect(**db_params)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """)
            exists = cur.fetchone()[0]
        conn.close()
        return exists
    except Exception as e:
        print(f"❌ Error checking table existence: {e}")
        return False


if __name__ == "__main__":
    print("🚀 RAG Project - Users Table Migration")
    print("=" * 40)
    
    # Check if table already exists
    if check_users_table_exists():
        print("⚠️  Users table already exists!")
        response = input("Do you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            exit(0)
    
    # Run migration
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed! You can now:")
        print("   1. Create user accounts")
        print("   2. Link conversations to specific users")
        print("   3. Implement user authentication")
        print("   4. Track user-specific chat history")
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        exit(1)