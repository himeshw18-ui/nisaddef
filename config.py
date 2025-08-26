import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Discord Bot Configuration - REQUIRED
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
    GUILD_ID = int(os.getenv('GUILD_ID', '0')) if os.getenv('GUILD_ID') else 0
    
    # Admin Configuration - REQUIRED
    ADMIN_CHANNEL_ID = int(os.getenv('ADMIN_CHANNEL_ID', '0')) if os.getenv('ADMIN_CHANNEL_ID') else 0
    ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0')) if os.getenv('ADMIN_USER_ID') else 0
    ACCOUNTS_CHANNEL_ID = int(os.getenv('ACCOUNTS_CHANNEL_ID', '0')) if os.getenv('ACCOUNTS_CHANNEL_ID') else 0
    
    # Pricing Configuration
    ACCOUNT_PRICE = float(os.getenv('ACCOUNT_PRICE', '0.50'))
    
    # Payment Configuration (Optional)
    BITCOIN_ADDRESS = os.getenv('BITCOIN_ADDRESS', '')
    MONERO_ADDRESS = os.getenv('MONERO_ADDRESS', '')
    ETHEREUM_ADDRESS = os.getenv('ETHEREUM_ADDRESS', '')
    
    # Indian Payment Methods (Optional)
    UPI_ID = os.getenv('UPI_ID', '')
    PAYTM_NUMBER = os.getenv('PAYTM_NUMBER', '')
    PHONEPE_UPI = os.getenv('PHONEPE_UPI', '')
    
    # Gift Card Instructions
    GIFT_CARD_INSTRUCTIONS = os.getenv('GIFT_CARD_INSTRUCTIONS', 'Send gift card codes to admin for instant processing')
    
    # Firebase Database Configuration - REQUIRED
    FIREBASE_SERVICE_ACCOUNT_KEY = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', '')
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'service-account-key.json')
    
    # Ticket Configuration - REQUIRED
    TICKET_CATEGORY_ID = int(os.getenv('TICKET_CATEGORY_ID', '0')) if os.getenv('TICKET_CATEGORY_ID') else 0
    
    # Shop Channel Name (where bot posts shop message)
    SHOP_CHANNEL_NAME = os.getenv('SHOP_CHANNEL_NAME', 'order-ticket')
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is set"""
        required_fields = [
            ('DISCORD_TOKEN', cls.DISCORD_TOKEN),
            ('GUILD_ID', cls.GUILD_ID),
            ('ADMIN_CHANNEL_ID', cls.ADMIN_CHANNEL_ID),
            ('ADMIN_USER_ID', cls.ADMIN_USER_ID),
        ]
        
        missing = []
        for field_name, field_value in required_fields:
            if not field_value or field_value in ['YOUR_BOT_TOKEN_HERE', 0]:
                missing.append(field_name)
        
        # Check Firebase configuration
        if not cls.FIREBASE_SERVICE_ACCOUNT_KEY and not cls.FIREBASE_SERVICE_ACCOUNT_PATH:
            missing.append('FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_PATH')
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True 