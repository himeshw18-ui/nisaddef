#!/usr/bin/env python3
"""
Startup script for the Private Account Selling Discord Bot
"""

import os
import sys
from config import Config

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import discord
        import firebase_admin
        import aiohttp
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_configuration():
    """Check if bot is properly configured"""
    print("\n🔧 Checking configuration...")
    
    try:
        Config.validate_config()
        print("✅ Configuration is valid")
        return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📝 Please configure the following in your .env file or config.py:")
        print("- DISCORD_TOKEN: Your Discord bot token")
        print("- GUILD_ID: Your Discord server ID")
        print("- ADMIN_CHANNEL_ID: Channel for admin notifications")
        print("- ADMIN_USER_ID: Your Discord user ID")
        print("- FIREBASE_SERVICE_ACCOUNT_KEY: Firebase configuration (JSON)")
        return False

def display_setup_info():
    """Display setup information"""
    print("🤖 Private Account Selling Discord Bot")
    print("=" * 50)
    print("💰 Price per account: $0.50 (min 2 accounts)")
    print("🎫 Automatic ticket system with private channels")
    print("💳 Gift card payments (Amazon/Google/Prepaid Cards)")
    print("👨‍💼 Manual admin approval workflow")
    print("🔥 Firebase cloud database")
    print()

def main():
    """Main startup function"""
    display_setup_info()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check configuration
    if not check_configuration():
        print("\n📋 Quick Setup Guide:")
        print("1. Create .env file with your configuration")
        print("2. Add your Discord bot token")
        print("3. Set up admin channel and user IDs")
        print("4. Add cryptocurrency addresses for payments")
        print("5. Run this script again")
        sys.exit(1)
    
    # Check Firebase connection
    if Config.FIREBASE_SERVICE_ACCOUNT_KEY or Config.FIREBASE_SERVICE_ACCOUNT_PATH:
        print("🔥 Firebase database configured")
    else:
        print("⚠️  Firebase database not configured - bot may not work properly")
    
    # Payment method info
    print("💳 Payment method: Gift Cards (Amazon, Google Play, Prepaid Visa/Mastercard)")
    print("🎫 Manual admin approval system enabled")
    
    print("\n🚀 Starting bot...")
    print("Use /shop command in Discord to display the purchase interface")
    print("Press Ctrl+C to stop the bot")
    print()
    
    # Import and run the bot
    try:
        import asyncio
        from bot import start_bot_with_server
        asyncio.run(start_bot_with_server())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error running bot: {e}")
        print("💡 Make sure Firebase is configured correctly")
        print("💡 Check that all Discord IDs are valid")
        print("💡 Verify your service account key is valid")
        sys.exit(1)

if __name__ == "__main__":
    main() 