import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from config import Config

class Database:
    def __init__(self):
        self.db = None
        
    def _ensure_db_initialized(self):
        """Ensure database is initialized, raise error if not"""
        if self.db is None:
            raise RuntimeError("❌ Firebase database not initialized. Please check Firebase configuration.")
        
    async def init_database(self):
        """Initialize Firebase connection"""
        print("🔧 Starting Firebase initialization...")
        
        try:
            if not firebase_admin._apps:
                # Initialize Firebase with service account key
                if os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'):
                    print("🔍 Found FIREBASE_SERVICE_ACCOUNT_KEY environment variable")
                    try:
                        service_account_info = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
                        print("✅ Successfully parsed Firebase service account JSON")
                        cred = credentials.Certificate(service_account_info)
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse Firebase service account JSON: {e}")
                        raise
                else:
                    print("🔍 Using FIREBASE_SERVICE_ACCOUNT_PATH (fallback)")
                    cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'service-account-key.json'))
                
                print("🔧 Initializing Firebase app...")
                firebase_admin.initialize_app(cred)
                print("✅ Firebase app initialized")
            else:
                print("✅ Firebase app already initialized")
            
            print("🔧 Creating Firestore client...")
            self.db = firestore.client()
            
            # Test the connection
            print("🔧 Testing Firestore connection...")
            test_ref = self.db.collection('_test').document('test')
            test_ref.set({'test': True})
            print("✅ Firestore connection test successful")
            
            print("✅ Firebase initialized successfully")
            
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            self.db = None
            raise
    
    async def create_order(self, user_id: int, username: str, quantity: int, total_price: float) -> str:
        """Create a new order"""
        doc_ref = self.db.collection('orders').document()
        order_data = {
            'user_id': user_id,
            'username': username,
            'quantity': quantity,
            'total_price': total_price,
            'status': 'pending',
            'payment_address': '',
            'payment_method': '',
            'created_at': firestore.SERVER_TIMESTAMP,
            'completed_at': None,
            'ticket_channel_id': None
        }
        doc_ref.set(order_data)
        return doc_ref.id
    
    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        doc_ref = self.db.collection('orders').document(order_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    async def update_order_status(self, order_id: str, status: str, completed_at: str = None):
        """Update order status"""
        doc_ref = self.db.collection('orders').document(order_id)
        update_data = {'status': status}
        if completed_at:
            update_data['completed_at'] = firestore.SERVER_TIMESTAMP
        doc_ref.update(update_data)
    
    async def add_account(self, email: str, password: str) -> bool:
        """Add a new account to the database"""
        try:
            # Check if account already exists
            accounts_ref = self.db.collection('accounts')
            query = accounts_ref.where('email', '==', email).limit(1)
            docs = query.get()
            
            if len(docs) > 0:
                return False  # Account already exists
            
            # Add new account
            doc_ref = accounts_ref.document()
            account_data = {
                'email': email,
                'password': password,
                'is_used': False,
                'used_by_user_id': None,
                'used_at': None,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            doc_ref.set(account_data)
            return True
        except Exception as e:
            print(f"Error adding account: {e}")
            return False
    
    async def get_available_accounts(self, quantity: int) -> List[Dict]:
        """Get available accounts for purchase"""
        accounts_ref = self.db.collection('accounts')
        query = accounts_ref.where('is_used', '==', False).limit(quantity)
        docs = query.get()
        
        accounts = []
        for doc in docs:
            account_data = doc.to_dict()
            account_data['id'] = doc.id
            accounts.append(account_data)
        
        return accounts
    
    async def mark_accounts_used(self, account_ids: List[str], user_id: int):
        """Mark accounts as used"""
        batch = self.db.batch()
        for account_id in account_ids:
            doc_ref = self.db.collection('accounts').document(account_id)
            batch.update(doc_ref, {
                'is_used': True,
                'used_by_user_id': user_id,
                'used_at': firestore.SERVER_TIMESTAMP
            })
        batch.commit()
    
    async def create_ticket(self, user_id: int, channel_id: int, order_id: str = None) -> str:
        """Create a new ticket"""
        doc_ref = self.db.collection('tickets').document()
        ticket_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'order_id': order_id,
            'status': 'open',
            'created_at': firestore.SERVER_TIMESTAMP,
            'closed_at': None
        }
        doc_ref.set(ticket_data)
        return doc_ref.id
    
    async def close_ticket(self, channel_id: int):
        """Close a ticket"""
        tickets_ref = self.db.collection('tickets')
        query = tickets_ref.where('channel_id', '==', channel_id)
        docs = query.get()
        
        for doc in docs:
            doc.reference.update({
                'status': 'closed',
                'closed_at': firestore.SERVER_TIMESTAMP
            })
    
    async def get_account_count(self) -> Dict[str, int]:
        """Get account statistics including reservations"""
        self._ensure_db_initialized()
        
        # Clean up expired reservations first
        await self.cleanup_expired_reservations()
        
        # Count total accounts
        accounts_ref = self.db.collection('accounts')
        total_docs = accounts_ref.get()
        total = len(total_docs)
        
        # Count used accounts
        used_query = accounts_ref.where('is_used', '==', True)
        used_docs = used_query.get()
        used = len(used_docs)
        
        # Count reserved accounts (active reservations)
        reservations_ref = self.db.collection('account_reservations')
        now = datetime.now()
        active_query = reservations_ref.where('status', '==', 'active').where('expires_at', '>', now)
        active_reservations = active_query.get()
        
        reserved_account_ids = set()
        for reservation_doc in active_reservations:
            reservation_data = reservation_doc.to_dict()
            account_ids = reservation_data.get('account_ids', [])
            reserved_account_ids.update(account_ids)
        
        reserved = len(reserved_account_ids)
        available = max(0, total - used - reserved)
        
        return {
            "available": available, 
            "total": total, 
            "used": used,
            "reserved": reserved
        }
    
    async def create_payment(self, order_id: str, payment_address: str, expected_amount: float) -> str:
        """Create a payment record"""
        doc_ref = self.db.collection('payments').document()
        payment_data = {
            'order_id': order_id,
            'payment_address': payment_address,
            'expected_amount': expected_amount,
            'received_amount': 0,
            'transaction_hash': '',
            'status': 'pending',
            'created_at': firestore.SERVER_TIMESTAMP,
            'confirmed_at': None
        }
        doc_ref.set(payment_data)
        return doc_ref.id
    
    async def reserve_accounts(self, order_id: str, quantity: int, expires_at: datetime) -> List[str]:
        """Reserve accounts for an order temporarily"""
        # Get currently reserved account IDs
        reservations_ref = self.db.collection('account_reservations')
        now = datetime.now()
        active_query = reservations_ref.where('status', '==', 'active').where('expires_at', '>', now)
        active_reservations = active_query.get()
        
        reserved_account_ids = set()
        for reservation_doc in active_reservations:
            reservation_data = reservation_doc.to_dict()
            account_ids = reservation_data.get('account_ids', [])
            reserved_account_ids.update(account_ids)
        
        # Get available accounts (not used and not reserved)
        accounts_ref = self.db.collection('accounts')
        available_query = accounts_ref.where('is_used', '==', False)
        available_docs = available_query.get()
        
        available_accounts = []
        for doc in available_docs:
            if doc.id not in reserved_account_ids:
                available_accounts.append(doc.id)
        
        if len(available_accounts) >= quantity:
            # Reserve the required quantity
            reserved_ids = available_accounts[:quantity]
            
            # Create reservation record
            reservation_ref = self.db.collection('account_reservations').document()
            reservation_data = {
                'order_id': order_id,
                'account_ids': reserved_ids,
                'reserved_at': firestore.SERVER_TIMESTAMP,
                'expires_at': expires_at,
                'status': 'active'
            }
            reservation_ref.set(reservation_data)
            
            return reserved_ids
        
        return []
    
    async def get_reserved_accounts(self, order_id: str) -> List[str]:
        """Get reserved account IDs for an order"""
        reservations_ref = self.db.collection('account_reservations')
        query = reservations_ref.where('order_id', '==', order_id).where('status', '==', 'active')
        docs = query.get()
        
        for doc in docs:
            reservation_data = doc.to_dict()
            return reservation_data.get('account_ids', [])
        
        return []
    
    async def confirm_reservation(self, order_id: str, user_id: int):
        """Confirm reservation and mark accounts as used"""
        # Get reserved account IDs
        reserved_ids = await self.get_reserved_accounts(order_id)
        
        if reserved_ids:
            # Mark accounts as used
            await self.mark_accounts_used(reserved_ids, user_id)
            
            # Mark reservation as completed
            reservations_ref = self.db.collection('account_reservations')
            query = reservations_ref.where('order_id', '==', order_id).where('status', '==', 'active')
            docs = query.get()
            
            for doc in docs:
                doc.reference.update({'status': 'completed'})
            
            return reserved_ids
        return []
    
    async def release_reservation(self, order_id: str):
        """Release reservation (accounts become available again)"""
        reservations_ref = self.db.collection('account_reservations')
        query = reservations_ref.where('order_id', '==', order_id).where('status', '==', 'active')
        docs = query.get()
        
        for doc in docs:
            doc.reference.update({'status': 'released'})
    
    async def cleanup_expired_reservations(self):
        """Remove expired reservations"""
        self._ensure_db_initialized()
        
        reservations_ref = self.db.collection('account_reservations')
        now = datetime.now()
        query = reservations_ref.where('status', '==', 'active').where('expires_at', '<', now)
        docs = query.get()
        
        for doc in docs:
            doc.reference.update({'status': 'expired'}) 