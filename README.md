# 🤖 Private Account Selling Discord Bot

A comprehensive Discord bot for selling Curso Pro accounts with anonymous payment processing, ticket system, and automated delivery.

## ✨ Features

- **Button-based Purchase Interface**: 1, 5, 10, or custom quantity purchases
- **Automatic Ticket System**: Private channels for each order
- **Instant DM Delivery**: Accounts sent directly to buyer's DMs
- **Admin Notifications**: Real-time alerts for orders
- **Anonymous Payments**: Bitcoin, Monero, Ethereum support
- **Stock Management**: Automatic account tracking

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env file
```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here
ADMIN_CHANNEL_ID=admin_channel_id
ADMIN_USER_ID=your_user_id
TICKET_CATEGORY_ID=ticket_category_id
ACCOUNT_PRICE=0.50
BITCOIN_ADDRESS=your_btc_address
MONERO_ADDRESS=your_xmr_address
```

### 3. Run Bot
```bash
python bot.py
```

## 📋 Commands

- `/shop` - Display purchase interface
- `/add_accounts` - Add accounts (Admin)
- `/stats` - View statistics (Admin)  
- `/complete_order` - Complete order (Admin)

## 💰 Anonymous Payment Methods

1. **Monero (XMR)** - Most private
2. **Bitcoin (BTC)** - Anonymous  
3. **Ethereum (ETH)** - Fast

## 🔄 How It Works

1. User clicks purchase button
2. Ticket channel created automatically
3. Payment address provided
4. Admin confirms payment
5. Accounts delivered via DM
6. Admin notified of completion

## 🛡️ Security

- Cryptocurrency payments only
- No personal data collection
- Private ticket system
- Admin-only verification 