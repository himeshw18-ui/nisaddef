#!/usr/bin/env python3
"""
Firebase Test Script for Discord Account Bot
Run this to test your Firebase connection before deploying
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

from database import Database

async def test_firebase():
    """Test Firebase database connection and basic operations"""
    
    print("🔥 Testing Firebase Connection...")
    print("-" * 50)
    
    # Initialize database
    try:
        db = Database()
        await db.init_database()
        print("✅ Firebase initialized successfully")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False
    
    print("-" * 50)
    
    # Test 1: Add a test account
    print("🧪 Test 1: Adding test account...")
    try:
        success = await db.add_account("test@example.com", "testpassword123")
        if success:
            print("✅ Test account added successfully")
        else:
            print("⚠️  Account already exists (this is ok)")
    except Exception as e:
        print(f"❌ Failed to add account: {e}")
        return False
    
    # Test 2: Get account statistics
    print("\n🧪 Test 2: Getting account statistics...")
    try:
        stats = await db.get_account_count()
        print(f"✅ Account stats: {stats}")
        
        if stats['total'] > 0:
            print("✅ Database has accounts")
        else:
            print("⚠️  No accounts in database yet")
            
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return False
    
    # Test 3: Create a test order
    print("\n🧪 Test 3: Creating test order...")
    try:
        order_id = await db.create_order(
            user_id=123456789, 
            username="testuser#1234", 
            quantity=1, 
            total_price=0.50
        )
        print(f"✅ Test order created with ID: {order_id}")
        
        # Get the order back
        order = await db.get_order(order_id)
        if order:
            print(f"✅ Order retrieved: {order['username']} - ${order['total_price']}")
        else:
            print("❌ Could not retrieve order")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create order: {e}")
        return False
    
    # Test 4: Account reservation (if we have accounts)
    print("\n🧪 Test 4: Testing account reservation...")
    try:
        if stats['available'] > 0:
            expires_at = datetime.now()
            reserved_ids = await db.reserve_accounts(order_id, 1, expires_at)
            if reserved_ids:
                print(f"✅ Reserved accounts: {reserved_ids}")
                
                # Release the reservation
                await db.release_reservation(order_id)
                print("✅ Released reservation")
            else:
                print("⚠️  No accounts available for reservation")
        else:
            print("⚠️  Skipping reservation test - no accounts available")
    except Exception as e:
        print(f"❌ Failed reservation test: {e}")
        return False
    
    print("-" * 50)
    print("🎉 All Firebase tests passed!")
    print("✅ Your Firebase database is ready for the Discord bot")
    print("-" * 50)
    
    return True

async def main():
    """Main test function"""
    
    print("🔥 Firebase Database Test for Discord Bot")
    print("=" * 60)
    
    # Check if Firebase config exists
    if not os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY') and not os.path.exists('service-account-key.json'):
        print("❌ Firebase configuration not found!")
        print("Please set FIREBASE_SERVICE_ACCOUNT_KEY environment variable")
        print("or place service-account-key.json in the bot directory")
        print("\nFollow FIREBASE_SETUP.md for detailed instructions")
        return
    
    success = await test_firebase()
    
    if success:
        print("🚀 Firebase is ready! You can now deploy your bot")
    else:
        print("💥 Firebase test failed. Check your configuration")
        print("See FIREBASE_SETUP.md for troubleshooting")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏸️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        print("Check your Firebase configuration and try again") 