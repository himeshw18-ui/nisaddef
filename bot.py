#!/usr/bin/env python3
"""
Discord Account Shop Bot
Compatible with Python 3.13+ via audioop workaround
"""

import sys
import os

# Force flush prints for Render logging
def debug_print(msg):
    print(msg)
    sys.stdout.flush()

debug_print(f"🐍 Python version: {sys.version}")
debug_print(f"🔧 Script started at: {__file__}")
debug_print(f"🔧 Current working directory: {os.getcwd()}")
debug_print(f"🔧 Python executable: {sys.executable}")

# CRITICAL: Apply audioop fix for Python 3.13+ BEFORE importing discord
if sys.version_info >= (3, 13):
    debug_print("🔧 Python 3.13+ detected - applying audioop compatibility fix...")
    # Import our audioop fix before discord.py
    import audioop_fix
else:
    debug_print("✅ Python < 3.13 - no audioop fix needed")

debug_print("📦 Importing Discord.py...")
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
        
        # Reserve accounts for 2 hours (plenty of time for admin approval)
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(hours=2)).isoformat()
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
        try:
            debug_print(f"🔧 Admin approve button clicked by {interaction.user.id} for order {self.order_id}")
            
            if interaction.user.id != Config.ADMIN_USER_ID:
                debug_print(f"❌ Non-admin user {interaction.user.id} tried to approve order")
                await interaction.response.send_message("❌ Only admin can approve orders.", ephemeral=True)
                return
            
            # Get order details
            order = await db.get_order(str(self.order_id))
            if not order:
                await interaction.response.send_message("❌ Order not found.", ephemeral=True)
                return
            
            # Confirm the reservation and get the reserved accounts
            confirmed_ids = await db.confirm_reservation(str(self.order_id), order['user_id'])
            if not confirmed_ids:
                await interaction.response.send_message("❌ No accounts were reserved for this order or reservation expired.", ephemeral=True)
                return
            
            # Get the account details for the confirmed IDs using Firebase
            accounts = []
            for account_id in confirmed_ids:
                account_doc = db.db.collection('accounts').document(account_id).get()
                if account_doc.exists:
                    account_data = account_doc.to_dict()
                    account_data['id'] = account_id
                    accounts.append(account_data)
            
            if not accounts:
                await interaction.response.send_message("❌ Could not retrieve account details.", ephemeral=True)
                return
            
            # Update order status to completed
            await db.update_order_status(str(self.order_id), 'completed')
            
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
            
        except Exception as e:
            debug_print(f"❌ Error in approve_order: {e}")
            import traceback
            debug_print(f"❌ Full traceback: {traceback.format_exc()}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred while processing the approval. Please check logs.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ An error occurred while processing the approval. Please check logs.", ephemeral=True)
            except Exception as followup_error:
                debug_print(f"❌ Could not send error message: {followup_error}")
    
    @discord.ui.button(label='❌ Reject', style=discord.ButtonStyle.red, custom_id='admin_reject_order')
    async def reject_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            debug_print(f"🔧 Admin reject button clicked by {interaction.user.id} for order {self.order_id}")
            
            if interaction.user.id != Config.ADMIN_USER_ID:
                debug_print(f"❌ Non-admin user {interaction.user.id} tried to reject order")
                await interaction.response.send_message("❌ Only admin can reject orders.", ephemeral=True)
                return
            
            # Show rejection reason modal
            modal = RejectionReasonModal(self.order_id, self.user_id)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            debug_print(f"❌ Error in reject_order: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred while processing the rejection.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ An error occurred while processing the rejection.", ephemeral=True)
            except:
                debug_print("❌ Could not send rejection error message")
    
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
            
            # Set user_ping for notifications (same logic as rejection flow)
            if hasattr(user, 'guild') and user in guild.members:
                user_ping = user.mention
            else:
                user_ping = f"**{user.name}**"
            
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
        try:
            # Acknowledge the interaction immediately
            await interaction.response.defer()
            
            # Release the reservation
            await db.release_reservation(self.order_id)
            
            # Update order status
            await db.update_order_status(self.order_id, 'rejected', datetime.now().isoformat())
            
            # Update shop message with released accounts
            await update_shop_message(interaction.guild)
            
            # Create user channel to explain rejection
            guild = interaction.guild
            category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
            
            # Try to get user - first as guild member, then as Discord user
            user = guild.get_member(self.user_id)
            if not user:
                try:
                    user = await guild.fetch_member(self.user_id)
                except:
                    try:
                        # User not in guild, but we can still DM them
                        user = await bot.fetch_user(self.user_id)
                    except:
                        print(f"Could not find user {self.user_id} for rejection notification")
                        # Update admin message and exit
                        embed = discord.Embed(
                            title="❌ Order Rejected",
                            description=f"Order #{self.order_id} has been rejected, but user {self.user_id} could not be found for notification.\nReason: {self.reason.value}",
                            color=discord.Color.red()
                        )
                        await interaction.edit_original_response(embed=embed, view=None)
                        return
            
            # Send DM notification first (works even if user left guild)
            try:
                dm_embed = discord.Embed(
                    title="❌ Order Rejected",
                    description=f"Your order #{self.order_id} has been rejected.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Reason", value=self.reason.value, inline=False)
                dm_embed.add_field(
                    name="What to do next:",
                    value="• Check your gift card code\n• Try with a different gift card\n• Contact admin if you have questions",
                    inline=False
                )
                
                await user.send(embed=dm_embed)
                print(f"Sent rejection DM notification to {user.name}")
                dm_sent = True
                
            except discord.Forbidden:
                print(f"Could not send rejection DM to {user.name}: DMs disabled")
                dm_sent = False
            except Exception as dm_error:
                print(f"Could not send rejection DM to {user.name}: {dm_error}")
                dm_sent = False
            
            # Only create channel if user is still in guild
            if hasattr(user, 'guild') and user in guild.members:
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
                
                # Add DM status to rejection channel
                if dm_sent:
                    await user_channel.send(f"📱 **Note:** A rejection notification has also been sent to your DMs.")
                else:
                    await user_channel.send(f"📝 **Note:** Could not send DM notification. Please check this channel for rejection details.")
                
                # Add close button
                close_embed = discord.Embed(
                    title="🎫 Channel Controls",
                    description="Click the button below to close this channel.",
                    color=discord.Color.light_grey()
                )
                close_view = TicketControlView()
                await user_channel.send(embed=close_embed, view=close_view)
            else:
                # User is not in guild - DM was sent but no channel created
                print(f"User {user.name} not in guild - rejection channel not created, DM sent instead")
            
            # Update admin message
            dm_status = "✅ DM sent" if dm_sent else "❌ DM failed"
            embed = discord.Embed(
                title="❌ Order Rejected",
                description=f"Order #{self.order_id} has been rejected.\nReason: {self.reason.value}",
                color=discord.Color.red()
            )
            embed.add_field(name="User Notification", value=f"{dm_status} to {user.name}", inline=True)
            if hasattr(user, 'guild') and user in guild.members:
                embed.add_field(name="Rejection Channel", value="✅ Created", inline=True)
            else:
                embed.add_field(name="Rejection Channel", value="❌ Not created (user not in guild)", inline=True)
            
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            debug_print(f"❌ Error in rejection modal: {e}")
            try:
                error_embed = discord.Embed(
                    title="❌ Error Processing Rejection",
                    description=f"An error occurred while processing the rejection: {str(e)}",
                    color=discord.Color.red()
                )
                if interaction.response.is_done():
                    await interaction.edit_original_response(embed=error_embed, view=None)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except Exception as followup_error:
                debug_print(f"❌ Could not send rejection error message: {followup_error}")

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

def create_shop_embed(available_count, total_count=None):
    """Create a standardized shop embed"""
    embed = discord.Embed(
        title="🛒 Curso Pro Account Shop - Live",
        description="Click the buttons below to purchase accounts instantly!",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Price per Account", value=f"${Config.ACCOUNT_PRICE:.2f}", inline=True)
    embed.add_field(name="📦 Available Stock", value=f"{available_count} accounts", inline=True)
    embed.add_field(name="⚡ Status", value="🟢 Online & Ready", inline=True)
    
    embed.add_field(
        name="🔥 Purchase Options",
        value="• **2 Accounts** - $1.00 (Minimum)\n• **5 Accounts** - $2.50\n• **10 Accounts** - $5.00\n• **Custom Amount** - 2+ accounts only",
        inline=False
    )
    
    embed.add_field(
        name="💳 Payment Methods (Gift Cards Only)",
        value="🛒 **Amazon Gift Cards ($, ₹)** - Most Popular\n📱 **Google Play Cards ($, ₹)** - Instant Processing\n💳 **Prepaid Visa/Mastercard ($, ₹)** - Universal\n\n💱 **Accepted Currencies:** USD ($) or Indian Rupees (₹) only",
        inline=False
    )
    
    embed.add_field(
        name="📋 Process",
        value="1️⃣ Click purchase button\n2️⃣ Private ticket created\n3️⃣ Send payment\n4️⃣ Accounts delivered to DM",
        inline=False
    )
    
    embed.set_footer(text="🚀 Instant delivery • 🔐 Anonymous payments • 💬 24/7 support")
    
    return embed

@bot.event
async def on_ready():
    start_time = asyncio.get_event_loop().time()
    debug_print(f'{bot.user} has logged in!')
    
    # Initialize Firebase database
    debug_print("🔧 Starting Firebase initialization...")
    await db.init_database()
    debug_print("✅ Firebase initialized successfully")
    
    # Add persistent views
    bot.add_view(PermanentPurchaseView())
    bot.add_view(TicketControlView())
    # Note: AdminApprovalView is dynamically created per order, not persistent
    
    # Sync commands first - Guild sync for immediate availability
    try:
        debug_print("🔄 Syncing slash commands to guild for immediate availability...")
        guild = bot.get_guild(Config.GUILD_ID)
        if guild:
            synced = await bot.tree.sync(guild=guild)
            debug_print(f"✅ Synced {len(synced)} command(s) to {guild.name} (immediate)")
        else:
            debug_print("⚠️ Guild not found, falling back to global sync (1 hour delay)")
            synced = await bot.tree.sync()
            debug_print(f"✅ Synced {len(synced)} command(s) globally (up to 1 hour)")
    except Exception as e:
        debug_print(f"❌ Failed to sync commands: {e}")
    
    # Auto-post shop message to order-ticket channel
    try:
        guild = bot.get_guild(Config.GUILD_ID)
        if guild:
            # Look for the order-ticket channel
            shop_channel = None
            for channel in guild.text_channels:
                if Config.SHOP_CHANNEL_NAME in channel.name.lower():
                    shop_channel = channel
                    break
            
            if shop_channel:
                debug_print(f"Found {Config.SHOP_CHANNEL_NAME} channel: {shop_channel.name}")
                
                # Get current account count
                try:
                    stats = await db.get_account_count()
                    available_count = stats['available']
                    total_count = stats['total']
                except Exception as e:
                    debug_print(f"⚠️ Could not get account count: {e}")
                    available_count = "?"
                    total_count = "?"
                
                # Create shop embed
                embed = create_shop_embed(available_count, total_count)
                view = PermanentPurchaseView()
                
                # Clear old shop messages from bot (optimized for speed)
                deleted_count = 0
                try:
                    # Only check recent messages (last 20) for faster startup
                    async for message in shop_channel.history(limit=20):
                        if message.author == bot.user:
                            try:
                                await message.delete()
                                deleted_count += 1
                            except discord.NotFound:
                                # Message already deleted
                                pass
                            except discord.Forbidden:
                                # No permissions to delete
                                break
                            except Exception as e:
                                # Other errors - continue but log
                                debug_print(f"⚠️ Could not delete message: {e}")
                                break
                except Exception as e:
                    debug_print(f"⚠️ Error during message cleanup: {e}")
                
                debug_print(f"Deleted {deleted_count} old messages")
                
                shop_message = await shop_channel.send(embed=embed, view=view)
                debug_print(f"✅ Shop message posted in {shop_channel.mention}")
                
            else:
                debug_print(f"❌ Could not find '{Config.SHOP_CHANNEL_NAME}' channel")
                
    except Exception as e:
        debug_print(f"❌ Error setting up shop: {e}")
    
    # Background tasks disabled per user request
    # Reservations will NOT auto-expire - admin must manually approve/reject all orders
    debug_print("ℹ️ Automatic reservation cleanup DISABLED - accounts stay reserved until admin acts")
    
    # Keep-alive handled by UptimeRobot - no Discord messages needed
    debug_print("✅ Bot keep-alive managed by UptimeRobot")
        
    debug_print("🎯 Bot is ready! Shop is live and users can start purchasing!")
    
    # Debug admin channel
    debug_print(f"Looking for admin channel with ID: {Config.ADMIN_CHANNEL_ID}")
    admin_channel = bot.get_channel(Config.ADMIN_CHANNEL_ID)
    if admin_channel:
        debug_print(f"✅ Found admin channel: {admin_channel.name} ({admin_channel.id})")
        try:
            test_embed = discord.Embed(
                title="🤖 Bot Started",
                description="Account shop bot is now online and ready!",
                color=discord.Color.green()
            )
            await admin_channel.send(embed=test_embed)
            debug_print("✅ Successfully sent test message to admin channel")
        except Exception as e:
            debug_print(f"❌ Error sending to admin channel: {e}")
    else:
        debug_print(f"❌ Admin channel not found with ID: {Config.ADMIN_CHANNEL_ID}")
        guild = bot.get_guild(Config.GUILD_ID)
        if guild:
            debug_print("Available channels:")
            for channel in guild.text_channels:
                debug_print(f"  - {channel.name} ({channel.id})")
        else:
            debug_print("❌ Guild not found either!")
    
    # Show initialization timing
    end_time = asyncio.get_event_loop().time()
    init_duration = round(end_time - start_time, 2)
    debug_print(f"🕒 Bot initialization completed in {init_duration} seconds")

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
            debug_print("Shop channel not found for update")
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
                value="🛒 **Amazon Gift Cards ($, ₹)** - Most Popular\n📱 **Google Play Cards ($, ₹)** - Instant Processing\n💳 **Prepaid Visa/Mastercard ($, ₹)** - Universal\n\n💱 **Accepted Currencies:** USD ($) or Indian Rupees (₹) only",
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
            debug_print(f"Updated shop message with {stats['available']} available accounts")
        
    except Exception as e:
        debug_print(f"Error updating shop message: {e}")

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
        value="🛒 **Amazon Gift Cards ($, ₹)** - Most Popular\n📱 **Google Play Cards ($, ₹)** - Instant Processing\n💳 **Prepaid Visa/Mastercard ($, ₹)** - Universal\n\n💱 **Accepted Currencies:** USD ($) or Indian Rupees (₹) only",
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

@bot.tree.command(name="admin_chat", description="Send a message as the bot to any channel (Admin only)")
async def admin_chat_command(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    """Allow admin to send messages as the bot to any channel"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    try:
        # Send the message to the specified channel
        await channel.send(message)
        
        # Confirm to admin
        embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Successfully sent message to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Channel", value=f"{channel.name} ({channel.id})", inline=True)
        embed.add_field(name="Message", value=f"```{message[:500]}{'...' if len(message) > 500 else ''}```", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        debug_print(f"Admin {interaction.user} sent message to #{channel.name}: {message[:100]}...")
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ No permission to send messages in {channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="send_instructions", description="Send customizable purchase instructions (Admin only)")
async def send_instructions_command(
    interaction: discord.Interaction, 
    channel: discord.TextChannel = None,
    title: str = "📋 How to Purchase Accounts - Complete Guide",
    description: str = "Follow these simple steps to purchase accounts through our automated bot system:",
    product_name: str = "accounts",
    support_info: str = "Message admin directly",
    footer_text: str = "🚀 Automated system • 🔐 Secure payments • 💬 24/7 support",
    currency_info: str = "USD ($) or Indian Rupees (₹)"
):
    """Send comprehensive instructions for account purchase through the bot"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    try:
        # Use provided channel or current channel
        target_channel = channel if channel else interaction.channel
        
        # Create comprehensive instructions embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🚀 Step 1: Start Purchase",
            value=f"• Look for the **shop message** with purchase buttons\n• Click on your desired quantity (2, 5, 10, or Custom)\n• A **private ticket** will be created for you automatically",
            inline=False
        )
        
        embed.add_field(
            name="🎁 Step 2: Prepare Gift Card",
            value=f"• Get a **gift card** in **{currency_info}**\n• Accepted: Amazon, Google Play, Prepaid Visa/Mastercard\n• Make sure the card has sufficient balance for your order",
            inline=False
        )
        
        embed.add_field(
            name="💳 Step 3: Submit Payment",
            value="• In your **private ticket**, you'll see a **gift card form**\n• Fill in:\n  - Gift card type (Amazon/Google Play/etc.)\n  - Complete gift card code\n• Submit the form and wait for admin approval",
            inline=False
        )
        
        embed.add_field(
            name=f"✅ Step 4: Get Your {product_name.title()}",
            value=f"• Admin will **verify your gift card** (usually within minutes)\n• Once approved, {product_name} are **delivered instantly**\n• You'll receive {product_name} in a **private channel** + **DM backup**\n• Each account includes email and password",
            inline=False
        )
        
        embed.add_field(
            name="💡 Important Tips",
            value=f"• **Only gift cards accepted** - no crypto, PayPal, etc.\n• **{currency_info}** only\n• Keep your **gift card receipt** until order is completed\n• Check your **DMs** for {product_name} delivery notifications",
            inline=False
        )
        
        embed.add_field(
            name="🆘 Need Help?",
            value=f"• **Bot not responding?** Try again in a few minutes\n• **Gift card rejected?** Double-check the code and try again\n• **Other issues?** {support_info}\n• All purchases are **manually verified** for security",
            inline=False
        )
        
        embed.add_field(
            name="🤖 How to Interact with Bot",
            value="• **Click buttons** on the shop message to start\n• **Fill forms** when prompted\n• **Wait for notifications** in your private ticket\n• **Check DMs** for delivery confirmations",
            inline=False
        )
        
        embed.set_footer(text=footer_text)
        
        # Send to target channel
        await target_channel.send(embed=embed)
        
        # Confirm to admin with customization details
        confirm_embed = discord.Embed(
            title="✅ Instructions Sent",
            description=f"Customized purchase instructions have been sent to {target_channel.mention}",
            color=discord.Color.green()
        )
        
        # Show customizations used (only if different from defaults)
        customizations = []
        if title != "📋 How to Purchase Accounts - Complete Guide":
            customizations.append(f"**Title:** {title}")
        if product_name != "accounts":
            customizations.append(f"**Product:** {product_name}")
        if support_info != "Message admin directly":
            customizations.append(f"**Support:** {support_info}")
        if currency_info != "USD ($) or Indian Rupees (₹)":
            customizations.append(f"**Currencies:** {currency_info}")
        if footer_text != "🚀 Automated system • 🔐 Secure payments • 💬 24/7 support":
            customizations.append(f"**Footer:** {footer_text[:50]}...")
            
        if customizations:
            confirm_embed.add_field(
                name="🎨 Customizations Applied",
                value="\n".join(customizations),
                inline=False
            )
        else:
            confirm_embed.add_field(
                name="📋 Content",
                value="Default instructions sent",
                inline=False
            )
            
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
        debug_print(f"Admin sent {'customized ' if customizations else ''}purchase instructions to #{target_channel.name}")
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ No permission to send messages in {target_channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="instructions_help", description="Show customization options for send_instructions command (Admin only)")
async def instructions_help_command(interaction: discord.Interaction):
    """Show all customization options for the send_instructions command"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎨 Instructions Customization Help",
        description="Here are all the parameters you can customize in `/send_instructions`:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📝 Basic Options",
        value="`channel:` Target channel (default: current)\n`title:` Main heading\n`description:` Opening description",
        inline=False
    )
    
    embed.add_field(
        name="🛍️ Product Options", 
        value="`product_name:` What you're selling (default: accounts)\n`currency_info:` Accepted currencies\n`support_info:` How to get help",
        inline=False
    )
    
    embed.add_field(
        name="🎨 Appearance",
        value="`footer_text:` Bottom text of embed",
        inline=False
    )
    
    embed.add_field(
        name="💡 Example Usage",
        value="```/send_instructions channel:#announcements product_name:premium_accounts title:🔥 Premium Account Store support_info:Open a ticket for help```",
        inline=False
    )
    
    embed.add_field(
        name="🔧 Default Values",
        value="• Title: 📋 How to Purchase Accounts - Complete Guide\n• Product: accounts\n• Currency: USD ($) or Indian Rupees (₹)\n• Support: Message admin directly\n• Footer: 🚀 Automated system • 🔐 Secure payments • 💬 24/7 support",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sync_commands", description="Sync bot commands to Discord (Admin only)")
async def sync_commands(interaction: discord.Interaction, scope: str = "guild"):
    """Sync bot commands to Discord - Admin only command"""
    if interaction.user.id != Config.ADMIN_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        synced_count = 0
        if scope.lower() == "global":
            # Sync globally (takes up to 1 hour to appear)
            synced = await bot.tree.sync()
            synced_count = len(synced)
            scope_text = "globally"
        else:
            # Sync to current guild (appears immediately)
            synced = await bot.tree.sync(guild=interaction.guild)
            synced_count = len(synced)
            scope_text = f"to {interaction.guild.name}"
        
        embed = discord.Embed(
            title="✅ Commands Synced",
            description=f"Successfully synced **{synced_count}** commands {scope_text}!",
            color=discord.Color.green()
        )
        
        # List the synced commands
        if synced:
            command_names = [f"• `/{cmd.name}`" for cmd in synced]
            embed.add_field(
                name="📝 Synced Commands",
                value="\n".join(command_names[:15]) + (f"\n... and {len(command_names)-15} more" if len(command_names) > 15 else ""),
                inline=False
            )
        
        embed.add_field(
            name="⏱️ Availability",
            value="Guild sync: **Immediate**\nGlobal sync: **Up to 1 hour**" if scope.lower() == "global" else "Commands should appear **immediately**",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed)
        debug_print(f"Admin synced {synced_count} commands {scope_text}")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Sync Failed",
            description=f"Failed to sync commands: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=error_embed)
        debug_print(f"❌ Command sync failed: {e}")

@bot.command(name='sync')
async def sync_text_command(ctx, scope: str = "guild"):
    """Backup text command to sync slash commands - Admin only"""
    if ctx.author.id != Config.ADMIN_USER_ID:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    try:
        synced_count = 0
        if scope.lower() == "global":
            synced = await bot.tree.sync()
            synced_count = len(synced)
            scope_text = "globally"
        else:
            synced = await bot.tree.sync(guild=ctx.guild)
            synced_count = len(synced)
            scope_text = f"to {ctx.guild.name}"
        
        embed = discord.Embed(
            title="✅ Commands Synced",
            description=f"Successfully synced **{synced_count}** commands {scope_text}!",
            color=discord.Color.green()
        )
        
        if synced:
            command_names = [f"• `/{cmd.name}`" for cmd in synced]
            embed.add_field(
                name="📝 Synced Commands",
                value="\n".join(command_names[:10]) + (f"\n... and {len(command_names)-10} more" if len(command_names) > 10 else ""),
                inline=False
            )
        
        embed.add_field(
            name="⏱️ Availability",
            value="Guild sync: **Immediate**\nGlobal sync: **Up to 1 hour**" if scope.lower() == "global" else "Commands should appear **immediately**",
            inline=False
        )
        
        await ctx.send(embed=embed)
        debug_print(f"Admin synced {synced_count} commands {scope_text} via text command")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Sync Failed",
            description=f"Failed to sync commands: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        debug_print(f"❌ Command sync failed: {e}")

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

# DISABLED: 5-minute cleanup task per user request
# @tasks.loop(minutes=5)  # Reduced frequency to save resources
# async def cleanup_expired_reservations():
#     """Background task to clean up expired reservations and update shop"""
#     try:
#         # Clean up expired reservations
#         old_count = await db.get_account_count()
#         await db.cleanup_expired_reservations()
#         new_count = await db.get_account_count()
#         
#         # Only update shop message if counts actually changed
#         if old_count != new_count:
#             guild = bot.get_guild(Config.GUILD_ID)
#             if guild:
#                 await update_shop_message(guild)
#                 debug_print(f"Updated shop: {old_count['available']} → {new_count['available']} available")
#             
#     except Exception as e:
#         debug_print(f"Error in cleanup task: {e}")


# Removed check_payments task to reduce server load
# All payments are handled manually by admin

# Keep-alive HTTP server for Render hosting
async def health_check(request):
    """Health check endpoint to keep Render awake"""
    try:
        stats = await db.get_account_count()
        return web.json_response({
            "status": "Bot is alive and running!",
            "bot_user": str(bot.user) if bot.user else "Not connected",
            "available_accounts": stats.get('available', 0),
            "total_accounts": stats.get('total', 0),
            "timestamp": datetime.now().isoformat()
        })
    except Exception:
        # Firebase not ready yet, return basic health check
        return web.json_response({
            "status": "Bot is alive and running!",
            "bot_user": str(bot.user) if bot.user else "Connecting...",
            "note": "Database initializing...",
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
    debug_print(f"✅ Keep-alive server running on port {port}")

async def start_bot_with_server():
    """Start both Discord bot and HTTP server"""
    try:
        # Start HTTP server first
        debug_print("🌐 Starting HTTP server for Render...")
        await start_web_server()
        debug_print("✅ HTTP server started")
        
        # Start Discord bot properly - no timeout needed
        debug_print(f"🤖 Connecting to Discord with token: {Config.DISCORD_TOKEN[:20]}...")
        debug_print("🔍 Attempting Discord connection...")
        debug_print(f"🔧 Bot intents: {bot.intents}")
        debug_print(f"🔧 Bot prefix: {bot.command_prefix}")
        
        # Start the bot - this runs indefinitely and includes on_ready processing
        debug_print("🚀 Starting Discord bot (this will run indefinitely)...")
        await bot.start(Config.DISCORD_TOKEN)
        
    except discord.LoginFailure as e:
        debug_print("❌ INVALID DISCORD TOKEN: Authentication failed")
        debug_print(f"❌ Token used: {Config.DISCORD_TOKEN[:20]}...")
        debug_print(f"❌ Login error: {e}")
        raise
    except discord.HTTPException as e:
        debug_print(f"❌ Discord HTTP error: {e}")
        debug_print(f"❌ Status: {e.status}, Response: {e.response}")
        raise
    except Exception as e:
        debug_print(f"❌ Error starting bot: {e}")
        import traceback
        debug_print(f"❌ Full traceback: {traceback.format_exc()}")
        raise
    finally:
        await payment_handler.close()

if __name__ == "__main__":
    import os
    
    debug_print("🚀 Starting Discord Account Shop Bot...")
    debug_print(f"🔧 Discord Token: {'✅ SET' if Config.DISCORD_TOKEN else '❌ MISSING'}")
    debug_print(f"🔧 Guild ID: {Config.GUILD_ID}")
    debug_print(f"🔧 Admin Channel: {Config.ADMIN_CHANNEL_ID}")
    debug_print(f"🔧 Firebase Key: {'✅ SET' if Config.FIREBASE_SERVICE_ACCOUNT_KEY else '❌ MISSING'}")
    
    # More detailed checks
    if not Config.DISCORD_TOKEN:
        debug_print("❌ CRITICAL: Discord token is missing!")
    if not Config.GUILD_ID:
        debug_print("❌ CRITICAL: Guild ID is missing!")
    if not Config.FIREBASE_SERVICE_ACCOUNT_KEY:
        debug_print("❌ CRITICAL: Firebase key is missing!")
    
    try:
        Config.validate_config()
        debug_print("✅ Configuration validation passed")
        
        # Run bot with HTTP server for Render hosting
        debug_print("🚀 Starting bot with HTTP server...")
        asyncio.run(start_bot_with_server())
        
    except ValueError as e:
        debug_print(f"❌ Configuration error: {e}")
        debug_print("Please check your configuration in config.py")
    except Exception as e:
        debug_print(f"❌ Error starting bot: {e}")
        import traceback
        debug_print(f"❌ Full traceback: {traceback.format_exc()}") 