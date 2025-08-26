import aiohttp
import asyncio
from typing import Dict, Optional
from config import Config
import hashlib
import uuid

class PaymentHandler:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
    
    def generate_payment_id(self, order_id: int, user_id: int) -> str:
        """Generate unique payment identifier"""
        data = f"{order_id}_{user_id}_{uuid.uuid4()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    async def create_bitcoin_payment(self, amount: float, order_id: int) -> Dict:
        """Create Bitcoin payment request"""
        payment_id = self.generate_payment_id(order_id, 0)
        
        # For Bitcoin, we'll use the configured address
        # In a real implementation, you'd generate unique addresses for each payment
        payment_data = {
            "payment_id": payment_id,
            "address": Config.BITCOIN_ADDRESS,
            "amount": amount,
            "currency": "BTC",
            "qr_code": f"bitcoin:{Config.BITCOIN_ADDRESS}?amount={amount}&label=Order_{order_id}",
            "explorer_url": f"https://blockstream.info/address/{Config.BITCOIN_ADDRESS}"
        }
        
        return payment_data
    
    async def create_monero_payment(self, amount: float, order_id: int) -> Dict:
        """Create Monero payment request (most anonymous option)"""
        payment_id = self.generate_payment_id(order_id, 0)
        
        # Monero provides the highest level of privacy
        payment_data = {
            "payment_id": payment_id,
            "address": Config.MONERO_ADDRESS,
            "amount": amount,
            "currency": "XMR",
            "qr_code": f"monero:{Config.MONERO_ADDRESS}?tx_amount={amount}&tx_payment_id={payment_id}",
            "explorer_url": "https://xmrchain.net/"
        }
        
        return payment_data
    
    async def create_ethereum_payment(self, amount: float, order_id: int) -> Dict:
        """Create Ethereum payment request"""
        payment_id = self.generate_payment_id(order_id, 0)
        
        payment_data = {
            "payment_id": payment_id,
            "address": Config.ETHEREUM_ADDRESS,
            "amount": amount,
            "currency": "ETH",
            "qr_code": f"ethereum:{Config.ETHEREUM_ADDRESS}?value={amount}&gas=21000",
            "explorer_url": f"https://etherscan.io/address/{Config.ETHEREUM_ADDRESS}"
        }
        
        return payment_data
    
    async def check_bitcoin_payment(self, address: str, expected_amount: float) -> Dict:
        """Check Bitcoin payment status using public API"""
        try:
            session = await self.get_session()
            
            # Using Blockstream API (no API key required)
            url = f"https://blockstream.info/api/address/{address}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check received amount
                    received_satoshis = data.get('chain_stats', {}).get('funded_txo_sum', 0)
                    received_btc = received_satoshis / 100000000  # Convert satoshis to BTC
                    
                    return {
                        "status": "confirmed" if received_btc >= expected_amount else "pending",
                        "received_amount": received_btc,
                        "expected_amount": expected_amount,
                        "confirmations": data.get('chain_stats', {}).get('funded_txo_count', 0)
                    }
        except Exception as e:
            print(f"Error checking Bitcoin payment: {e}")
        
        return {"status": "error", "received_amount": 0, "expected_amount": expected_amount}
    
    async def get_crypto_price_usd(self, crypto: str) -> float:
        """Get current crypto price in USD"""
        try:
            session = await self.get_session()
            
            # Using CoinGecko API (free, no API key required)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get(crypto, {}).get('usd', 0)
        except Exception as e:
            print(f"Error getting crypto price: {e}")
        
        return 0
    
    async def calculate_crypto_amount(self, usd_amount: float, crypto: str) -> float:
        """Calculate crypto amount needed for USD amount"""
        crypto_mapping = {
            "bitcoin": "bitcoin",
            "btc": "bitcoin", 
            "monero": "monero",
            "xmr": "monero",
            "ethereum": "ethereum",
            "eth": "ethereum"
        }
        
        crypto_id = crypto_mapping.get(crypto.lower(), crypto.lower())
        price_usd = await self.get_crypto_price_usd(crypto_id)
        
        if price_usd > 0:
            return round(usd_amount / price_usd, 8)
        
        return 0
    
    def get_available_payment_methods(self) -> Dict:
        """Get available payment methods based on configuration"""
        methods = {}
        
        # Low-fee options for small amounts
        methods["gift_cards"] = {
            "name": "Digital Gift Cards 🇮🇳",
            "description": "Amazon/Flipkart cards (No fees, Most Anonymous)",
            "emoji": "🎁"
        }
        
        methods["upi_crypto"] = {
            "name": "UPI → Crypto P2P 🇮🇳",
            "description": "Buy crypto with UPI, send to us (~1-2% fees)",
            "emoji": "₿"
        }
        
        methods["upi"] = {
            "name": "UPI Direct 🇮🇳",
            "description": "PayTM/PhonePe/GPay (Instant, Low Privacy)",
            "emoji": "📱"
        }
        
        methods["lightning"] = {
            "name": "Bitcoin Lightning ⚡",
            "description": "Instant Bitcoin with ~$0.01 fees",
            "emoji": "⚡"
        }
        
        methods["cashapp"] = {
            "name": "Cash App 🇺🇸",
            "description": "$CashTag payments (No fees)",
            "emoji": "💸"
        }
        
        # Crypto options
        if Config.BITCOIN_ADDRESS:
            methods["bitcoin"] = {
                "name": "Bitcoin (BTC)",
                "description": "Anonymous Bitcoin payment (High fees for small amounts)",
                "emoji": "₿"
            }
        
        if Config.MONERO_ADDRESS:
            methods["monero"] = {
                "name": "Monero (XMR)", 
                "description": "Private Monero payment (Most Anonymous)",
                "emoji": "🔒"
            }
        
        # Low-fee crypto alternatives
        methods["tron"] = {
            "name": "TRON (TRX)",
            "description": "Low-fee crypto (~$0.01 fees)",
            "emoji": "🔴"
        }
        
        methods["polygon"] = {
            "name": "Polygon USDC",
            "description": "Stablecoin with minimal fees (~$0.001)",
            "emoji": "🟣"
        }
        
        return methods 