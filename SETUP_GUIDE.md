# 📋 Complete Setup Guide

## Step 1: Discord Bot Creation

### 1.1 Create Discord Application
1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name it "Account Shop Bot" (or your preferred name)
4. Go to "Bot" section in left sidebar
5. Click "Add Bot"
6. Copy the **Token** (this is your `DISCORD_TOKEN`)

### 1.2 Bot Permissions
In the "Bot" section, enable these permissions:
- Send Messages
- Use Slash Commands
- Embed Links
- Manage Channels
- Read Message History
- Manage Messages

### 1.3 Invite Bot to Server
1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select permissions: `Administrator` (for simplicity)
4. Copy the generated URL and invite bot to your server

## Step 2: Get Discord IDs

### 2.1 Enable Developer Mode
1. Discord Settings → Advanced → Enable "Developer Mode"

### 2.2 Get Required IDs
Right-click and "Copy ID" for each:

- **Server ID** (`GUILD_ID`): Right-click your server name
- **Your User ID** (`ADMIN_USER_ID`): Right-click your username
- **Admin Channel ID** (`ADMIN_CHANNEL_ID`): Right-click your admin notifications channel
- **Ticket Category ID** (`TICKET_CATEGORY_ID`): Right-click the category where tickets will be created

## Step 3: Anonymous Payment Setup

### Option 1: Monero (Most Anonymous) ⭐⭐⭐⭐⭐

**Why Monero?**
- Complete transaction privacy
- Untraceable payments
- No public transaction history

**Setup:**
1. Download official Monero wallet: https://www.getmonero.org/downloads/
2. Create new wallet
3. Copy your receive address
4. Add to config as `MONERO_ADDRESS`

### Option 2: Bitcoin (Semi-Anonymous) ⭐⭐⭐⭐

**Privacy Tips:**
- Use hardware wallet (Ledger, Trezor)
- Never reuse addresses
- Consider Bitcoin mixing services

**Setup:**
1. Download Electrum: https://electrum.org/
2. Create new wallet
3. Get receive address
4. Add to config as `BITCOIN_ADDRESS`

### Option 3: Ethereum (Fast) ⭐⭐⭐

**Setup:**
1. Install MetaMask extension
2. Create new wallet
3. Copy wallet address
4. Add to config as `ETHEREUM_ADDRESS`

## Step 4: Configuration

### 4.1 Create .env File
Create `.env` file in bot directory:

```env
# Discord Configuration
DISCORD_TOKEN=your_bot_token_from_step_1
GUILD_ID=your_server_id
ADMIN_CHANNEL_ID=your_admin_channel_id
ADMIN_USER_ID=your_user_id
TICKET_CATEGORY_ID=your_ticket_category_id

# Pricing
ACCOUNT_PRICE=0.50

# Payment Addresses (add at least one)
BITCOIN_ADDRESS=your_bitcoin_address
MONERO_ADDRESS=your_monero_address
ETHEREUM_ADDRESS=your_ethereum_address
```

### 4.2 Verify Configuration
Run the startup script to check everything:
```bash
python run.py
```

## Step 5: Add Accounts

### 5.1 Use Command
In Discord, use the admin command:
```
/add_accounts email1@example.com:password1,email2@example.com:password2
```

### 5.2 Format Rules
- Separate email and password with `:`
- Separate multiple accounts with `,`
- No spaces around separators

**Example:**
```
/add_accounts test1@curso.com:pass123,test2@curso.com:pass456,test3@curso.com:pass789
```

## Step 6: Server Setup

### 6.1 Create Channels
Create these channels in your Discord server:
- `#admin-notifications` (for order alerts)
- `#shop` (where users will use /shop command)

### 6.2 Create Category
- Create category called "Tickets" or "Orders"
- This is where individual order tickets will be created

### 6.3 Set Permissions
- Admin channels: Only you can see
- Shop channel: Everyone can see, only you can manage
- Ticket category: Bot needs manage channels permission

## Step 7: Testing

### 7.1 Test Purchase Flow
1. Run `/shop` in your shop channel
2. Click a purchase button
3. Verify ticket channel is created
4. Check payment options appear
5. Test DM delivery with `/complete_order`

### 7.2 Test Admin Features
- `/stats` - Check account statistics
- `/add_accounts` - Add test accounts
- `/complete_order 1` - Complete first order

## Step 8: Privacy & Security

### 8.1 Server Security
- Use VPS with anonymous payment (Bitcoin/Monero)
- Configure firewall
- Use VPN/Tor for server access
- Regular security updates

### 8.2 Payment Privacy
- Use fresh crypto addresses for each order
- Consider crypto mixing for Bitcoin
- Monero provides privacy by default
- Never link payments to real identity

### 8.3 Data Protection
- Regularly backup database
- Delete completed order data
- Don't log sensitive information
- Use encrypted storage

## Troubleshooting

### Bot Not Responding
- Check bot token is correct
- Verify bot has necessary permissions
- Check console for error messages

### Tickets Not Creating
- Verify `TICKET_CATEGORY_ID` is correct
- Check bot has "Manage Channels" permission
- Ensure category exists in server

### Payment Methods Not Showing
- Add crypto addresses to `.env` file
- Restart bot after config changes
- Check addresses are valid format

### DM Delivery Failed
- User has DMs disabled
- Admin gets notification automatically
- Send accounts manually in ticket channel

## Advanced Features

### Custom Pricing
Edit `config.py`:
```python
ACCOUNT_PRICE = 0.75  # New price per account
```

### Multiple Payment Methods
Add multiple addresses:
```env
BITCOIN_ADDRESS=bc1qexample1
MONERO_ADDRESS=4Aexample1
ETHEREUM_ADDRESS=0xexample1
```

### Automatic Payment Detection
- Bitcoin: Partially supported via blockchain APIs
- Monero: Manual verification recommended
- Ethereum: Can be implemented with web3 libraries

## Support

If you encounter issues:
1. Check console logs for detailed errors
2. Verify all configuration values
3. Test with small orders first
4. Ensure compliance with local laws

## Legal Disclaimer

- Ensure you own the accounts being sold
- Comply with local laws and regulations
- Consider tax implications of crypto payments
- Implement proper terms of service
- This bot is for educational purposes 