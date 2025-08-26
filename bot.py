#!/usr/bin/env python3
"""
Discord Account Shop Bot
Requires Python 3.11 (NOT 3.13 - audioop module issue)
"""

import sys
import os

# CRITICAL: Check Python version before importing discord.py
if sys.version_info >= (3, 13):
    print("❌ ERROR: Python 3.13+ detected!")
    print("❌ discord.py requires Python 3.11 due to audioop module removal in 3.13")
    print("❌ Please use Python 3.11.0 as specified in runtime.txt")
    print(f"❌ Current Python version: {sys.version}")
    sys.exit(1)
elif sys.version_info < (3, 11):
    print("❌ ERROR: Python version too old!")
    print("❌ This bot requires Python 3.11 or newer (but NOT 3.13)")
    print(f"❌ Current Python version: {sys.version}")
    sys.exit(1)

print(f"✅ Python version OK: {sys.version}")

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
import random
import string
import threading
from aiohttp import web
import aiohttp

from config import Config
from database import Database
from payment_utils import PaymentHandler

# Bot setup
intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = Database()
payment_handler = PaymentHandler()

class PermanentPurchaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='2 Accounts - $1.00', style=discord.ButtonStyle.green, emoji='2️⃣', custom_id='giftcard_buy_2')
    async def buy_2_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 2)
    
    @discord.ui.button(label='5 Accounts - $2.50', style=discord.ButtonStyle.green, emoji='5️⃣', custom_id='giftcard_buy_5')
    async def buy_5_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 5)
    
    @discord.ui.button(label='10 Accounts - $5.00', style=discord.ButtonStyle.green, emoji='🔟', custom_id='giftcard_buy_10')
    async def buy_10_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 10)
    
    @discord.ui.button(label='Custom Amount', style=discord.ButtonStyle.blurple, emoji='🔢', custom_id='giftcard_buy_custom')
    async def buy_custom_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomAmountModal()
        await interaction.response.send_modal(modal)
    
    async def handle_purchase(self, interaction: discord.Interaction, quantity: int):
        """Handle account purchase with gift card"""
        try:
            # Check if enough accounts are available
            stats = await db.get_account_count()
            if stats['available'] < quantity:
                embed = discord.Embed(
                    title="❌ Insufficient Stock",
                    description=f"Sorry, we only have {stats['available']} accounts available. Please contact admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Calculate total price
            total_price = quantity * Config.ACCOUNT_PRICE
            
            # Show gift card form
            modal = GiftCardModal(quantity, total_price)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            print(f"Error in handle_purchase: {e}")
            try:
                embed = discord.Embed(
                    title="⚠️ Please Try Again",
                    description="There was a temporary issue. Please click the button again.",
                    color=discord.Color.orange()
                )
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    async def notify_admin_new_order(self, order_id: int, user: discord.User, quantity: int, total_price: float):
        """Notify admin of new order"""
        admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(
                title="🔔 New Order Received",
                description=f"Order #{order_id}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Customer", value=f"{user.mention} ({user})", inline=True)
            embed.add_field(name="Quantity", value=f"{quantity} accounts", inline=True)
            embed.add_field(name="Total", value=f"${total_price:.2f}", inline=True)
            embed.add_field(name="Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            
            await admin_channel.send(embed=embed)

class PurchaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout
    
    @discord.ui.button(label='1 Account - $0.50', style=discord.ButtonStyle.green, emoji='1️⃣')
    async def buy_1_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 1)
    
    @discord.ui.button(label='5 Accounts - $2.50', style=discord.ButtonStyle.green, emoji='5️⃣')
    async def buy_5_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 5)
    
    @discord.ui.button(label='10 Accounts - $5.00', style=discord.ButtonStyle.green, emoji='🔟')
    async def buy_10_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_purchase(interaction, 10)
    
    @discord.ui.button(label='Custom Amount', style=discord.ButtonStyle.blurple, emoji='🔢')
    async def buy_custom_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomAmountModal()
        await interaction.response.send_modal(modal)
    
    async def handle_purchase(self, interaction: discord.Interaction, quantity: int):
        """Handle account purchase"""
        # Check if enough accounts are available
        stats = await db.get_account_count()
        if stats['available'] < quantity:
            embed = discord.Embed(
                title="❌ Insufficient Stock",
                description=f"Sorry, we only have {stats['available']} accounts available. Please contact admin.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calculate total price
        total_price = quantity * Config.ACCOUNT_PRICE
        
        # Create order
        order_id = await db.create_order(
            interaction.user.id,
            str(interaction.user),
            quantity,
            total_price
        )
        
        # Create ticket channel
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add admin access
        admin_user = guild.get_member(Config.ADMIN_USER_ID)
        if admin_user:
            overwrites[admin_user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel_name = f"order-{order_id}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )
        
        # Update order with ticket channel
        await db.create_ticket(interaction.user.id, ticket_channel.id, order_id)
        
        # Create payment options
        payment_methods = payment_handler.get_available_payment_methods()
        
        embed = discord.Embed(
            title="🎫 Order Created",
            description=f"Your order #{order_id} has been created!\nTicket: {ticket_channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Quantity", value=f"{quantity} accounts", inline=True)
        embed.add_field(name="Total Price", value=f"${total_price:.2f}", inline=True)
        embed.add_field(name="Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Send payment info to ticket channel
        payment_embed = discord.Embed(
            title=f"💳 Payment Required - Order #{order_id}",
            description=f"**Customer:** {interaction.user.mention}\n**Quantity:** {quantity} accounts\n**Total:** ${total_price:.2f}",
            color=discord.Color.blue()
        )
        
        if payment_methods:
            payment_view = PaymentMethodView(order_id, total_price)
            await ticket_channel.send(embed=payment_embed, view=payment_view)
        else:
            payment_embed.add_field(
                name="⚠️ Payment Methods Not Configured",
                value="Please contact admin to complete payment.",
                inline=False
            )
            await ticket_channel.send(embed=payment_embed)
        
        # Notify admin
        await self.notify_admin_new_order(order_id, interaction.user, quantity, total_price)
    
    async def notify_admin_new_order(self, order_id: int, user: discord.User, quantity: int, total_price: float):
        """Notify admin of new order"""
        admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(
                title="🔔 New Order Received",
                description=f"Order #{order_id}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Customer", value=f"{user.mention} ({user})", inline=True)
            embed.add_field(name="Quantity", value=f"{quantity} accounts", inline=True)
            embed.add_field(name="Total", value=f"${total_price:.2f}", inline=True)
            embed.add_field(name="Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            
            await admin_channel.send(embed=embed)

class GiftCardModal(discord.ui.Modal, title='Gift Card Payment'):
    def __init__(self, quantity: int, total_price: float):
        super().__init__()
        self.quantity = quantity
        self.total_price = total_price
    
    gift_card_type = discord.ui.TextInput(
        label='Gift Card Type',
        placeholder='Amazon / Google Play / Visa/Mastercard',
        min_length=3,
        max_length=20
    )
    
    gift_card_code = discord.ui.TextInput(
        label='Gift Card Code',
        placeholder='Enter your gift card code',
        min_length=10,
        max_length=50,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        card_type = self.gift_card_type.value.lower().strip()
        card_code = self.gift_card_code.value.strip()
        
        # Validate gift card type
        valid_types = ["amazon", "google", "google play", "visa", "mastercard", "prepaid"]
        if not any(valid_type in card_type for valid_type in valid_types):
            embed = discord.Embed(
                title="❌ Invalid Gift Card Type",
                description="Please use: Amazon, Google Play, or Prepaid Visa/Mastercard only.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Basic validation of gift card code format
        if not self.validate_gift_card_format(card_type, card_code):
            embed = discord.Embed(
                title="❌ Invalid Gift Card Format",
                description="Please check your gift card code format and try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create order in database
        order_id = await db.create_order(
            interaction.user.id,
            str(interaction.user),
            self.quantity,
            self.total_price
        )
        
        # Reserve accounts for 10 minutes
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
        reserved_ids = await db.reserve_accounts(order_id, self.quantity, expires_at)
        
        if not reserved_ids:
            embed = discord.Embed(
                title="❌ Unable to Reserve Accounts",
                description="Not enough accounts available for reservation. Please try again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Send to admin for approval
        await self.send_admin_approval(interaction, order_id, card_type, card_code, len(reserved_ids))
        
        # Confirm to user
        embed = discord.Embed(
            title="✅ Gift Card Submitted",
            description=f"Order #{order_id} submitted for verification.\nYou'll receive an update shortly!",
            color=discord.Color.green()
        )
        embed.add_field(name="Quantity", value=f"{self.quantity} accounts", inline=True)
        embed.add_field(name="Total", value=f"${self.total_price:.2f}", inline=True)
        embed.add_field(name="Card Type", value=card_type.title(), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def validate_gift_card_format(self, card_type: str, card_code: str) -> bool:
        """Basic validation of gift card code formats"""
        # Remove spaces and hyphens
        clean_code = card_code.replace(" ", "").replace("-", "")
        
        if "amazon" in card_type:
            # Amazon: Usually 14-15 alphanumeric characters
            return len(clean_code) >= 10 and clean_code.isalnum()
        
        elif "google" in card_type:
            # Google Play: Usually 20 characters, letters and numbers
            return len(clean_code) >= 15 and clean_code.isalnum()
        
        elif "visa" in card_type or "mastercard" in card_type or "prepaid" in card_type:
            # Prepaid cards: Usually 16 digits
            return len(clean_code) >= 12 and clean_code.isdigit()
        
        return len(clean_code) >= 10  # Basic fallback
    
    async def send_admin_approval(self, interaction: discord.Interaction, order_id: int, card_type: str, card_code: str, reserved_count: int):
        """Send gift card to admin for approval"""
        admin_channel = interaction.guild.get_channel(Config.ADMIN_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(
                title="🎁 New Gift Card Order - ACCOUNTS RESERVED",
                description=f"Order #{order_id} requires verification\n⏰ **10 minutes to approve/reject**",
                color=discord.Color.orange()
            )
            embed.add_field(name="Customer", value=f"{interaction.user.mention} ({interaction.user})", inline=False)
            embed.add_field(name="Quantity", value=f"{self.quantity} accounts", inline=True)
            embed.add_field(name="Reserved", value=f"✅ {reserved_count} accounts", inline=True)
            embed.add_field(name="Total", value=f"${self.total_price:.2f}", inline=True)
            embed.add_field(name="Card Type", value=card_type.title(), inline=True)
            embed.add_field(name="Gift Card Code", value=f"```{card_code}```", inline=False)
            embed.add_field(name="⏰ Auto-Release", value=f"<t:{int((datetime.now() + timedelta(minutes=10)).timestamp())}:R>", inline=True)
            embed.add_field(name="Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            
            view = AdminApprovalView(order_id, interaction.user.id)
            await admin_channel.send(embed=embed, view=view)

class CustomAmountModal(discord.ui.Modal, title='Custom Amount Purchase'):
    def __init__(self):
        super().__init__()
    
    quantity = discord.ui.TextInput(
        label='Number of Accounts (Minimum 2)',
        placeholder='Enter quantity (e.g., 15)',
        min_length=1,
        max_length=3
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty < 2:
                raise ValueError("Minimum 2 accounts required")
            if qty > 1000:  # Reasonable limit
                raise ValueError("Quantity too large")
            
            purchase_view = PermanentPurchaseView()
            await purchase_view.handle_purchase(interaction, qty)
            
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid Input", 
                description="Please enter a valid number (minimum 2 accounts).",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class AdminApprovalView(discord.ui.View):
    def __init__(self, order_id: int, user_id: int):
        super().__init__(timeout=None)
        self.order_id = order_id
        self.user_id = user_id
    
    @discord.ui.button(label='✅ Approve', style=discord.ButtonStyle.green, custom_id='admin_approve_order')
    async def approve_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != Config.ADMIN_USER_ID:
            await interaction.response.send_message("❌ Only admin can approve orders.", ephemeral=True)
            return
        
        # Get order details
        order = await db.get_order(self.order_id)
        if not order:
            await interaction.response.send_message("❌ Order not found.", ephemeral=True)
            return
        
        # Confirm the reservation and get the reserved accounts
        confirmed_ids = await db.confirm_reservation(self.order_id, order['user_id'])
        if not confirmed_ids:
            await interaction.response.send_message("❌ No accounts were reserved for this order or reservation expired.", ephemeral=True)
            return
        
        # Get the account details for the confirmed IDs
        async with aiosqlite.connect(db.db_path) as conn:
            placeholders = ','.join('?' * len(confirmed_ids))
            cursor = await conn.execute(f"""
                SELECT * FROM accounts WHERE id IN ({placeholders})
            """, confirmed_ids)
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            accounts = [dict(zip(columns, row)) for row in rows]
        
        # Update order status
        await db.update_order_status(self.order_id, 'completed', datetime.now().isoformat())
        
        # Create user channel and send accounts
        await self.create_user_channel_and_deliver(interaction, order, accounts)
        
        # Update admin message
        embed = discord.Embed(
            title="✅ Order Approved & Completed",
            description=f"Order #{self.order_id} has been approved and accounts delivered.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Update shop message with new stock count
        await update_shop_message(interaction.guild)
    
    @discord.ui.button(label='❌ Reject', style=discord.ButtonStyle.red, custom_id='admin_reject_order')
    async def reject_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != Config.ADMIN_USER_ID:
            await interaction.response.send_message("❌ Only admin can reject orders.", ephemeral=True)
            return
        
        # Show rejection reason modal
        modal = RejectionReasonModal(self.order_id, self.user_id)
        await interaction.response.send_modal(modal)
    
    async def create_user_channel_and_deliver(self, interaction: discord.Interaction, order: dict, accounts: list):
        """Create a private channel for the user and deliver accounts"""
        try:
            guild = interaction.guild
            
            # Try to get category, if not found, use None (will create in default location)
            category = None
            if Config.TICKET_CATEGORY_ID:
                category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
            
            # Create channel permissions - try multiple ways to get user
            user = guild.get_member(order['user_id'])
            if not user:
                # Try fetching the user if not cached
                try:
                    user = await guild.fetch_member(order['user_id'])
                except:
                    try:
                        # Try getting user from bot
                        user = await bot.fetch_user(order['user_id'])
                    except:
                        print(f"User {order['user_id']} not found anywhere")
                        return
            
            print(f"Found user: {user.name} ({user.id})")
            
            # Add admin to permissions
            admin_user = guild.get_member(Config.ADMIN_USER_ID)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            }
            
            # Add user permissions - this user should definitely see the channel
            overwrites[user] = discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
            
            # Add admin permissions
            if admin_user:
                overwrites[admin_user] = discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True, 
                    manage_messages=True,
                    read_message_history=True
                )
            
            # Create user channel with safer name
            safe_username = ''.join(c for c in user.name if c.isalnum() or c in '-_')[:20]
            channel_name = f"delivery-{self.order_id}-{safe_username}"
            
            print(f"Creating channel: {channel_name}")
            user_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites
            )
            
            print(f"Created delivery channel: {user_channel.name}")
            
        except Exception as e:
            print(f"Error creating user channel: {e}")
            # Try to send to admin channel instead
            admin_channel = guild.get_channel(Config.ADMIN_CHANNEL_ID)
            if admin_channel:
                error_embed = discord.Embed(
                    title="⚠️ Channel Creation Failed",
                    description=f"Could not create delivery channel for {user.mention}. Sending accounts here instead.",
                    color=discord.Color.orange()
                )
                await admin_channel.send(embed=error_embed)
                user_channel = admin_channel
            else:
                return
        
        try:
            # Send success message
            success_embed = discord.Embed(
                title="🎉 Order Approved!",
                description=f"Your order #{self.order_id} has been approved and processed.",
                color=discord.Color.green()
            )
            success_embed.add_field(name="Quantity", value=f"{order['quantity']} accounts", inline=True)
            success_embed.add_field(name="Total Paid", value=f"${order['total_price']:.2f}", inline=True)
            success_embed.add_field(name="Status", value="✅ Completed", inline=True)
            
            # Send welcome message with proper user ping
            welcome_msg = f"🎉 **{user.mention}** Your Curso Pro accounts are ready!"
            await user_channel.send(welcome_msg, embed=success_embed)
            print(f"Sent success message to {user_channel.name}")
            
            # Send account details
            account_list = []
            for i, account in enumerate(accounts, 1):
                account_list.append(f"**Account {i}:**\n• Email: `{account['email']}`\n• Password: `{account['password']}`")
            
            accounts_embed = discord.Embed(
                title="📧 Your Curso Pro Accounts",
                description=f"Here are your {len(accounts)} accounts:",
                color=discord.Color.blue()
            )
            accounts_embed.add_field(
                name="🔐 Account Details",
                value="\n\n".join(account_list),
                inline=False
            )
            accounts_embed.add_field(
                name="📝 Important Notes",
                value="• Change passwords after first login\n• Don't share these credentials\n• Contact support if any issues",
                inline=False
            )
            accounts_embed.set_footer(text="Thank you for your purchase!")
            
            await user_channel.send(embed=accounts_embed)
            print(f"Sent {len(accounts)} accounts to {user_channel.name}")
            
            # Add close button
            close_embed = discord.Embed(
                title="🎫 Channel Controls",
                description="Click the button below to close this channel when you're done.",
                color=discord.Color.light_grey()
            )
            close_view = TicketControlView()
            await user_channel.send(embed=close_embed, view=close_view)
            print(f"Added close button to {user_channel.name}")
            
            # Notify admin that delivery is complete
            admin_channel = guild.get_channel(Config.ADMIN_CHANNEL_ID)
            if admin_channel:
                admin_notification = discord.Embed(
                    title="✅ Order Delivered Successfully",
                    description=f"Order #{self.order_id} has been delivered to {user_ping}",
                    color=discord.Color.green()
                )
                admin_notification.add_field(name="Delivery Channel", value=user_channel.mention, inline=True)
                admin_notification.add_field(name="Accounts Sent", value=f"{len(accounts)} accounts", inline=True)
                admin_notification.add_field(name="User ID", value=f"{user.id}", inline=True)
                await admin_channel.send(embed=admin_notification)
            
            # Also send DM to user as backup
            try:
                dm_embed = discord.Embed(
                    title="🎉 Your Order is Ready!",
                    description=f"Your order #{self.order_id} has been processed. Check the delivery channel or contact admin.",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Order Details", value=f"{len(accounts)} accounts for ${order['total_price']:.2f}", inline=False)
                await user.send(embed=dm_embed)
                print(f"Sent DM notification to {user.name}")
            except Exception as dm_error:
                print(f"Could not send DM to {user.name}: {dm_error}")
                # Add note to delivery channel that DM failed
                await user_channel.send(f"📝 **Note:** Could not send DM notification. Please check this channel for your accounts.")
                
        except Exception as e:
            print(f"Error sending accounts: {e}")
            # Send error to admin
            admin_channel = interaction.guild.get_channel(Config.ADMIN_CHANNEL_ID)
            if admin_channel:
                error_embed = discord.Embed(
                    title="❌ Account Delivery Failed",
                    description=f"Error delivering accounts to {user.mention}: {str(e)}",
                    color=discord.Color.red()
                )
                await admin_channel.send(embed=error_embed)

class RejectionReasonModal(discord.ui.Modal, title='Rejection Reason'):
    def __init__(self, order_id: int, user_id: int):
        super().__init__()
        self.order_id = order_id
        self.user_id = user_id
    
    reason = discord.ui.TextInput(
        label='Reason for Rejection',
        placeholder='e.g., Invalid gift card, Already used, Wrong amount...',
        min_length=5,
        max_length=200,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Release the reservation
        await db.release_reservation(self.order_id)
        
        # Update order status
        await db.update_order_status(self.order_id, 'rejected', datetime.now().isoformat())
        
        # Update shop message with released accounts
        await update_shop_message(interaction.guild)
        
        # Create user channel to explain rejection
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
        user = guild.get_member(self.user_id)
        
        if user:
            # Create permissions similar to delivery channel
            admin_user = guild.get_member(Config.ADMIN_USER_ID)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Only add user permissions if they're a guild member
            if hasattr(user, 'guild') and user in guild.members:
                overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            if admin_user:
                overwrites[admin_user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            safe_username = ''.join(c for c in user.name if c.isalnum() or c in '-_')[:20]
            channel_name = f"rejected-{self.order_id}-{safe_username}"
            
            print(f"Creating rejection channel: {channel_name}")
            user_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites
            )
            
            # Send rejection message
            rejection_embed = discord.Embed(
                title="❌ Order Rejected",
                description=f"Your order #{self.order_id} has been rejected.",
                color=discord.Color.red()
            )
            rejection_embed.add_field(name="Reason", value=self.reason.value, inline=False)
            rejection_embed.add_field(
                name="What to do next:",
                value="• Check your gift card code\n• Try with a different gift card\n• Contact admin if you have questions",
                inline=False
            )
            
            # Send message with user ping if possible, otherwise just use their name
            if hasattr(user, 'guild') and user in guild.members:
                user_ping = user.mention
            else:
                user_ping = f"**{user.name}**"
            
            await user_channel.send(f"❌ Hello {user_ping}, unfortunately your order was rejected:", embed=rejection_embed)
            
            # Add close button
            close_embed = discord.Embed(
                title="🎫 Channel Controls",
                description="Click the button below to close this channel.",
                color=discord.Color.light_grey()
            )
            close_view = TicketControlView()
            await user_channel.send(embed=close_embed, view=close_view)
        
        # Update admin message
        embed = discord.Embed(
            title="❌ Order Rejected",
            description=f"Order #{self.order_id} has been rejected.\nReason: {self.reason.value}",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class PaymentMethodView(discord.ui.View):
    def __init__(self, order_id: int, usd_amount: float):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.order_id = order_id
        self.usd_amount = usd_amount
    
    @discord.ui.button(label='Bitcoin (BTC)', style=discord.ButtonStyle.grey, emoji='₿')
    async def pay_with_bitcoin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not Config.BITCOIN_ADDRESS:
            await interaction.response.send_message("Bitcoin payments not configured.", ephemeral=True)
            return
        
        crypto_amount = await payment_handler.calculate_crypto_amount(self.usd_amount, "bitcoin")
        payment_data = await payment_handler.create_bitcoin_payment(crypto_amount, self.order_id)
        
        embed = discord.Embed(
            title="₿ Bitcoin Payment",
            description=f"Send **{crypto_amount:.8f} BTC** to complete your order",
            color=discord.Color.orange()
        )
        embed.add_field(name="Address", value=f"```{payment_data['address']}```", inline=False)
        embed.add_field(name="Amount", value=f"{crypto_amount:.8f} BTC", inline=True)
        embed.add_field(name="USD Value", value=f"${self.usd_amount:.2f}", inline=True)
        embed.add_field(name="Payment ID", value=payment_data['payment_id'], inline=True)
        embed.set_footer(text="Payment will be automatically detected. Please wait for confirmation.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='Monero (XMR)', style=discord.ButtonStyle.grey, emoji='🔒')
    async def pay_with_monero(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not Config.MONERO_ADDRESS:
            await interaction.response.send_message("Monero payments not configured.", ephemeral=True)
            return
        
        crypto_amount = await payment_handler.calculate_crypto_amount(self.usd_amount, "monero")
        payment_data = await payment_handler.create_monero_payment(crypto_amount, self.order_id)
        
        embed = discord.Embed(
            title="🔒 Monero Payment (Most Anonymous)",
            description=f"Send **{crypto_amount:.8f} XMR** to complete your order",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Address", value=f"```{payment_data['address']}```", inline=False)
        embed.add_field(name="Amount", value=f"{crypto_amount:.8f} XMR", inline=True)
        embed.add_field(name="USD Value", value=f"${self.usd_amount:.2f}", inline=True)
        embed.add_field(name="Payment ID", value=payment_data['payment_id'], inline=True)
        embed.set_footer(text="Monero provides maximum privacy. Manually confirm payment with admin.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.red, emoji='🔒', custom_id='ticket_close_channel')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow ticket creator or admin to close
        if interaction.user.id != Config.ADMIN_USER_ID:
            # Check if user is the ticket creator
            channel = interaction.channel
            if not channel.name.startswith('order-') or str(interaction.user.id) not in channel.name:
                await interaction.response.send_message("You don't have permission to close this ticket.", ephemeral=True)
                return
        
        await db.close_ticket(interaction.channel.id)
        
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="This ticket will be deleted in 10 seconds.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        
        await asyncio.sleep(10)
        await interaction.channel.delete()

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    
    # Initialize Firebase database
    await db.init_database()
    
    # Add persistent views
    bot.add_view(PermanentPurchaseView())
    bot.add_view(TicketControlView())
    
    # Sync commands first
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    # Auto-post shop message to order-ticket channel
    try:
        guild = bot.get_guild(Config.GUILD_ID)
        if guild:
            # Look for the order-ticket channel
            shop_channel = None
            for channel in guild.text_channels:
                if "order-ticket" in channel.name.lower():
                    shop_channel = channel
                    break
            
            if shop_channel:
                print(f"Found order-ticket channel: {shop_channel.name}")
                
                # Post shop message
                stats = await db.get_account_count()
                
                embed = discord.Embed(
                    title="🛒 Curso Pro Account Shop - Live",
                    description="Click the buttons below to purchase accounts instantly!",
                    color=discord.Color.green()
                )
                embed.add_field(name="💰 Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
                embed.add_field(name="📦 Available Stock", value=f"{stats['available']} accounts", inline=True)
                embed.add_field(name="⚡ Status", value="🟢 Online & Ready", inline=True)
                
                embed.add_field(
                    name="🔥 Purchase Options",
                    value="• **2 Accounts** - $1.00 (Minimum)\n• **5 Accounts** - $2.50\n• **10 Accounts** - $5.00\n• **Custom Amount** - 2+ accounts only",
                    inline=False
                )
                
                embed.add_field(
                    name="💳 Payment Methods (Gift Cards Only)",
                    value="🛒 **Amazon Gift Cards** - Most Popular\n📱 **Google Play Cards** - Instant Processing\n💳 **Prepaid Visa/Mastercard** - Universal",
                    inline=False
                )
                
                embed.add_field(
                    name="📋 Process",
                    value="1️⃣ Click purchase button\n2️⃣ Private ticket created\n3️⃣ Send payment\n4️⃣ Accounts delivered to DM",
                    inline=False
                )
                
                embed.set_footer(text="🚀 Instant delivery • 🔐 Anonymous payments • 💬 24/7 support")
                
                view = PermanentPurchaseView()
                
                # Clear ALL old shop messages from bot
                deleted_count = 0
                async for message in shop_channel.history(limit=100):
                    if message.author == bot.user:
                        try:
                            await message.delete()
                            deleted_count += 1
                        except:
                            pass
                
                print(f"Deleted {deleted_count} old messages")
                
                shop_message = await shop_channel.send(embed=embed, view=view)
                print(f"✅ Shop message posted in {shop_channel.mention}")
                
            else:
                print(f"❌ Could not find 'order-ticket' channel")
                
    except Exception as e:
        print(f"❌ Error setting up shop: {e}")
    
    # Start background tasks (optimized for low resource usage)
    try:
        if not cleanup_expired_reservations.is_running():
            cleanup_expired_reservations.start()
            print("✅ Started reservation cleanup task (every 5 minutes)")
    except Exception as e:
        print(f"Warning: Could not start background tasks: {e}")
        
    print("🎯 Bot is ready! Shop is live and users can start purchasing!")
    
    # Debug admin channel
    print(f"Looking for admin channel with ID: {Config.ADMIN_CHANNEL_ID}")
    admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
    if admin_channel:
        print(f"✅ Found admin channel: {admin_channel.name} ({admin_channel.id})")
        try:
            test_embed = discord.Embed(
                title="🤖 Bot Started",
                description="Account shop bot is now online and ready!",
                color=discord.Color.green()
            )
            await admin_channel.send(embed=test_embed)
            print("✅ Successfully sent test message to admin channel")
        except Exception as e:
            print(f"❌ Error sending to admin channel: {e}")
    else:
        print(f"❌ Admin channel not found with ID: {Config.ADMIN_CHANNEL_ID}")
        guild = bot.get_guild(Config.GUILD_ID)
        if guild:
            print("Available channels:")
            for channel in guild.text_channels:
                print(f"  - {channel.name} ({channel.id})")
        else:
            print("❌ Guild not found either!")

async def update_shop_message(guild):
    """Update the shop message with current stock count"""
    try:
        # Find the order-ticket channel
        shop_channel = None
        for channel in guild.text_channels:
            if "order-ticket" in channel.name.lower():
                shop_channel = channel
                break
        
        if not shop_channel:
            print("Shop channel not found for update")
            return
        
        # Get current stats
        stats = await db.get_account_count()
        
        # Find the shop message (last message from bot with "Shop" in title)
        shop_message = None
        async for message in shop_channel.history(limit=10):
            if (message.author == bot.user and 
                message.embeds and 
                "Shop" in message.embeds[0].title):
                shop_message = message
                break
        
        if shop_message:
            # Create updated embed
            embed = discord.Embed(
                title="🛒 Curso Pro Account Shop - Live",
                description="Click the buttons below to purchase accounts instantly!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
            embed.add_field(name="📦 Available Stock", value=f"{stats['available']} accounts", inline=True)
            if stats.get('reserved', 0) > 0:
                embed.add_field(name="⏳ Reserved", value=f"{stats['reserved']} accounts", inline=True)
            else:
                embed.add_field(name="⚡ Status", value="🟢 Online & Ready", inline=True)
            
            embed.add_field(
                name="🔥 Purchase Options",
                value="• **2 Accounts** - $1.00 (Minimum)\n• **5 Accounts** - $2.50\n• **10 Accounts** - $5.00\n• **Custom Amount** - 2+ accounts only",
                inline=False
            )
            
            embed.add_field(
                name="💳 Payment Methods (Gift Cards Only)",
                value="🛒 **Amazon Gift Cards** - Most Popular\n📱 **Google Play Cards** - Instant Processing\n💳 **Prepaid Visa/Mastercard** - Universal",
                inline=False
            )
            
            embed.add_field(
                name="📋 Process",
                value="1️⃣ Click purchase button\n2️⃣ Private ticket created\n3️⃣ Send payment\n4️⃣ Accounts delivered to DM",
                inline=False
            )
            
            embed.set_footer(text="🚀 Instant delivery • 🔐 Anonymous payments • 💬 24/7 support")
            
            # Update the message with same view
            view = PermanentPurchaseView()
            await shop_message.edit(embed=embed, view=view)
            print(f"Updated shop message with {stats['available']} available accounts")
        
    except Exception as e:
        print(f"Error updating shop message: {e}")

@bot.tree.command(name="shop", description="Display the account shop")
async def shop_command(interaction: discord.Interaction):
    """Display the main shop interface"""
    stats = await db.get_account_count()
    
    embed = discord.Embed(
        title="🛒 Curso Pro Account Shop",
        description="Choose how many accounts you'd like to purchase:",
        color=discord.Color.blue()
    )
    embed.add_field(name="💰 Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
    embed.add_field(name="📦 Available Stock", value=f"{stats['available']} accounts", inline=True)
    if stats.get('reserved', 0) > 0:
        embed.add_field(name="⏳ Reserved", value=f"{stats['reserved']} accounts", inline=True)
    else:
        embed.add_field(name="⚡ Status", value="🟢 Online", inline=True)
    
    embed.add_field(
        name="🔥 Purchase Options",
        value="• **2 Accounts** - $1.00 (Minimum)\n• **5 Accounts** - $2.50\n• **10 Accounts** - $5.00\n• **Custom Amount** - 2+ accounts only",
        inline=False
    )
    
    embed.add_field(
        name="💳 Payment Methods (Gift Cards Only)",
        value="🛒 **Amazon Gift Cards** - Most Popular\n📱 **Google Play Cards** - Instant Processing\n💳 **Prepaid Visa/Mastercard** - Universal",
        inline=False
    )
    
    embed.set_footer(text="All accounts are delivered instantly after gift card verification")
    
    view = PermanentPurchaseView()
    await interaction.response.send_message(embed=embed, view=view)

# Admin Commands
@bot.tree.command(name="add_accounts", description="Add accounts to the database (Admin only)")
async def add_accounts_command(interaction: discord.Interaction, accounts: str):
    """Add accounts in format: email1:password1,email2:password2"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    try:
        account_pairs = accounts.split(',')
        added_count = 0
        errors = []
        
        for pair in account_pairs:
            pair = pair.strip()
            if ':' not in pair:
                errors.append(f"Invalid format: {pair}")
                continue
            
            email, password = pair.split(':', 1)
            email = email.strip()
            password = password.strip()
            
            if await db.add_account(email, password):
                added_count += 1
            else:
                errors.append(f"Account already exists: {email}")
        
        embed = discord.Embed(
            title="✅ Accounts Added",
            description=f"Successfully added {added_count} accounts",
            color=discord.Color.green()
        )
        
        if errors:
            embed.add_field(name="⚠️ Errors", value="\n".join(errors[:10]), inline=False)
        
        # Show updated stock
        stats = await db.get_account_count()
        embed.add_field(name="📦 Updated Stock", value=f"{stats['available']} accounts available", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Update the shop message with new stock count
        await update_shop_message(interaction.guild)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="stats", description="View bot statistics (Admin only)")
async def stats_command(interaction: discord.Interaction):
    """View bot statistics"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    stats = await db.get_account_count()
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.blue()
    )
    embed.add_field(name="📦 Total Accounts", value=stats['total'], inline=True)
    embed.add_field(name="✅ Available", value=stats['available'], inline=True)
    embed.add_field(name="💸 Sold", value=stats['used'], inline=True)
    embed.add_field(name="💰 Revenue", value=f"${stats['used'] * Config.ACCOUNT_PRICE:.2f}", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_shop", description="Set up permanent shop in current channel (Admin only)")
async def setup_shop_command(interaction: discord.Interaction):
    """Set up a permanent shop message with real-time updates"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    stats = await db.get_account_count()
    
    embed = discord.Embed(
        title="🛒 Curso Pro Account Shop - Live",
        description="Click the buttons below to purchase accounts instantly!",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
    embed.add_field(name="📦 Available Stock", value=f"{stats['available']} accounts", inline=True)
    embed.add_field(name="⚡ Status", value="🟢 Online & Ready", inline=True)
    
    embed.add_field(
        name="🔥 Purchase Options",
        value="• **1 Account** - $0.50\n• **5 Accounts** - $2.50\n• **10 Accounts** - $5.00\n• **Custom Amount** - Any quantity you need",
        inline=False
    )
    
    embed.add_field(
        name="💳 Anonymous Payment Methods",
        value="🔒 **Monero (XMR)** - Most Private\n₿ **Bitcoin (BTC)** - Anonymous\n⟠ **Ethereum (ETH)** - Fast",
        inline=False
    )
    
    embed.add_field(
        name="📋 Process",
        value="1️⃣ Click purchase button\n2️⃣ Private ticket created\n3️⃣ Send payment\n4️⃣ Accounts delivered to DM",
        inline=False
    )
    
    embed.set_footer(text="🚀 Instant delivery • 🔐 Anonymous payments • 💬 24/7 support")
    
    view = PermanentPurchaseView()
    
    await interaction.response.send_message(embed=embed, view=view)
    
    # Also send confirmation to admin
    admin_embed = discord.Embed(
        title="✅ Permanent Shop Setup",
        description=f"Shop interface created in {interaction.channel.mention}",
        color=discord.Color.green()
    )
    admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
    if admin_channel and admin_channel != interaction.channel:
        await admin_channel.send(embed=admin_embed)

@bot.tree.command(name="complete_order", description="Manually complete an order (Admin only)")
async def complete_order_command(interaction: discord.Interaction, order_id: int):
    """Manually complete an order and deliver accounts"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    try:
        order = await db.get_order(order_id)
        if not order:
            await interaction.response.send_message("❌ Order not found.", ephemeral=True)
            return
        
        if order['status'] == 'completed':
            await interaction.response.send_message("❌ Order already completed.", ephemeral=True)
            return
        
        # Get available accounts
        accounts = await db.get_available_accounts(order['quantity'])
        if len(accounts) < order['quantity']:
            await interaction.response.send_message("❌ Not enough accounts available.", ephemeral=True)
            return
        
        # Mark accounts as used
        account_ids = [acc['id'] for acc in accounts]
        await db.mark_accounts_used(account_ids, order['user_id'])
        
        # Update order status
        await db.update_order_status(order_id, 'completed', datetime.now().isoformat())
        
        # Send accounts to user
        user = bot.get_user(order['user_id'])
        if user:
            await send_accounts_to_user(user, accounts, order_id)
        
        embed = discord.Embed(
            title="✅ Order Completed",
            description=f"Order #{order_id} has been completed and accounts sent to user.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def send_accounts_to_user(user: discord.User, accounts: List[dict], order_id: int):
    """Send account details to user via DM"""
    try:
        account_list = []
        for i, account in enumerate(accounts, 1):
            account_list.append(f"**Account {i}:**\n• Email: `{account['email']}`\n• Password: `{account['password']}`")
        
        embed = discord.Embed(
            title="🎉 Your Curso Pro Accounts",
            description=f"Order #{order_id} - {len(accounts)} accounts",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📧 Account Details",
            value="\n\n".join(account_list),
            inline=False
        )
        embed.add_field(
            name="🔐 Important Notes",
            value="• Change passwords after first login\n• Don't share these credentials\n• Contact support if any issues",
            inline=False
        )
        embed.set_footer(text="Thank you for your purchase!")
        
        await user.send(embed=embed)
        
        # Notify admin channel
        admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
        if admin_channel:
            notify_embed = discord.Embed(
                title="✅ Accounts Delivered",
                description=f"Order #{order_id} - {len(accounts)} accounts sent to {user.mention}",
                color=discord.Color.green()
            )
            await admin_channel.send(embed=notify_embed)
            
    except discord.Forbidden:
        # User has DMs disabled
        admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(
                title="⚠️ DM Delivery Failed",
                description=f"Could not send accounts to {user.mention} - DMs disabled",
                color=discord.Color.orange()
            )
            await admin_channel.send(embed=embed)

@tasks.loop(minutes=5)  # Reduced frequency to save resources
async def cleanup_expired_reservations():
    """Background task to clean up expired reservations and update shop"""
    try:
        # Clean up expired reservations
        old_count = await db.get_account_count()
        await db.cleanup_expired_reservations()
        new_count = await db.get_account_count()
        
        # Only update shop message if counts actually changed
        if old_count != new_count:
            guild = bot.get_guild(Config.GUILD_ID)
            if guild:
                await update_shop_message(guild)
                print(f"Updated shop: {old_count['available']} → {new_count['available']} available")
            
    except Exception as e:
        print(f"Error in cleanup task: {e}")

# Removed check_payments task to reduce server load
# All payments are handled manually by admin

# Keep-alive HTTP server for Render hosting
async def health_check(request):
    """Health check endpoint to keep Render awake"""
    stats = await db.get_account_count()
    return web.json_response({
        "status": "Bot is alive and running!",
        "bot_user": str(bot.user) if bot.user else "Not connected",
        "available_accounts": stats.get('available', 0),
        "total_accounts": stats.get('total', 0),
        "timestamp": datetime.now().isoformat()
    })

async def start_web_server():
    """Start HTTP server for keep-alive"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', health_check)
    
    # Get port from environment (Render provides PORT)
    port = int(os.getenv('PORT', 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Keep-alive server running on port {port}")

async def start_bot_with_server():
    """Start both Discord bot and HTTP server"""
    try:
        # Start HTTP server first
        await start_web_server()
        
        # Start Discord bot
        await bot.start(Config.DISCORD_TOKEN)
        
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        await payment_handler.close()

if __name__ == "__main__":
    import os
    
    try:
        Config.validate_config()
        
        # Run bot with HTTP server for Render hosting
        asyncio.run(start_bot_with_server())
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your configuration in config.py")
    except Exception as e:
        print(f"Error starting bot: {e}") 