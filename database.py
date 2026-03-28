from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import string
import uuid
import re

db = SQLAlchemy()

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    title = db.Column(db.String(200), default='New Conversation')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with chat history
    messages = db.relationship('ChatHistory', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<ChatSession {self.id}: {self.title}>"


class Couple(db.Model):
    __tablename__ = 'couples'
    
    id = db.Column(db.Integer, primary_key=True)
    boy_name = db.Column(db.String(100), nullable=False)
    girl_name = db.Column(db.String(100), nullable=False)
    boy_mobile = db.Column(db.String(20), nullable=False)
    girl_mobile = db.Column(db.String(20), nullable=False)
    boy_age = db.Column(db.Integer, nullable=False)
    girl_age = db.Column(db.Integer, nullable=False)
    anniversary_date = db.Column(db.String(20), nullable=False)
    boy_id = db.Column(db.String(100), unique=True, nullable=False)
    girl_id = db.Column(db.String(100), unique=True, nullable=False)
    chat_password = db.Column(db.String(100), nullable=False, default='1234')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    chat_sessions = db.relationship('ChatSession', backref='couple', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='couple', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='couple', lazy=True, cascade='all, delete-orphan')
    
    def clean_name_for_id(self, name):
        """
        Clean name to create a valid ID:
        - Remove special characters
        - Replace spaces with hyphens
        - Convert to uppercase
        """
        if not name:
            return ''
        # Remove special characters except spaces and hyphens
        cleaned = re.sub(r'[^a-zA-Z\s-]', '', name)
        # Replace spaces with hyphens
        cleaned = re.sub(r'\s+', '-', cleaned)
        # Remove multiple consecutive hyphens
        cleaned = re.sub(r'-+', '-', cleaned)
        # Strip hyphens from start and end
        cleaned = cleaned.strip('-')
        # Convert to uppercase
        return cleaned.upper()
    
    def generate_unique_id(self, gender, name=None):
        """
        Generate a unique ID based on the individual's name
        Format: FU-{cleaned_name}-{B/G}
        Example: FU-JOHN-B or FU-JANE-G
        """
        # Get name based on gender
        if name is None:
            if gender == 'boy' and hasattr(self, 'boy_name'):
                name = self.boy_name
            elif gender == 'girl' and hasattr(self, 'girl_name'):
                name = self.girl_name
            else:
                name = ''
        
        # Clean the name
        cleaned_name = self.clean_name_for_id(name)
        
        # If name is empty or cleaning resulted in empty string, use fallback
        if not cleaned_name:
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            cleaned_name = random_part
        
        suffix = 'B' if gender == 'boy' else 'G'
        
        # Create base ID
        base_id = f"FU-{cleaned_name}-{suffix}"
        
        # Check if ID already exists and add counter if needed
        counter = 1
        while True:
            new_id = base_id if counter == 1 else f"FU-{cleaned_name}{counter}-{suffix}"
            
            # Check if this ID already exists
            if gender == 'boy':
                existing = Couple.query.filter_by(boy_id=new_id).first()
            else:
                existing = Couple.query.filter_by(girl_id=new_id).first()
            
            if not existing:
                return new_id
            
            counter += 1
    
    def save(self):
        """Save couple to database and generate unique IDs if not set"""
        # Generate IDs if they don't exist
        if not self.boy_id:
            self.boy_id = self.generate_unique_id('boy', self.boy_name)
        if not self.girl_id:
            self.girl_id = self.generate_unique_id('girl', self.girl_name)
        
        db.session.add(self)
        db.session.commit()
        return self
    
    @staticmethod
    def verify_login(unique_id, user_type):
        """Verify login credentials"""
        if not unique_id or not user_type:
            return None
            
        try:
            if user_type == 'boy':
                return Couple.query.filter_by(boy_id=unique_id).first()
            else:
                return Couple.query.filter_by(girl_id=unique_id).first()
        except Exception as e:
            print(f"Login verification error: {e}")
            return None
    
    @staticmethod
    def verify_chat_password(couple_id, password):
        """Verify chat password for a couple"""
        try:
            couple = Couple.query.get(couple_id)
            if couple and couple.chat_password == password:
                return True
            return False
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def to_dict(self):
        """Convert object to dictionary with SIMPLE values (no complex objects)"""
        try:
            return {
                'id': int(self.id) if self.id else 0,
                'boy_name': str(self.boy_name) if self.boy_name else '',
                'girl_name': str(self.girl_name) if self.girl_name else '',
                'boy_mobile': str(self.boy_mobile) if self.boy_mobile else '',
                'girl_mobile': str(self.girl_mobile) if self.girl_mobile else '',
                'boy_age': int(self.boy_age) if self.boy_age else 0,
                'girl_age': int(self.girl_age) if self.girl_age else 0,
                'anniversary_date': str(self.anniversary_date) if self.anniversary_date else '',
                'boy_id': str(self.boy_id) if self.boy_id else '',
                'girl_id': str(self.girl_id) if self.girl_id else '',
                'chat_password': str(self.chat_password) if self.chat_password else '',
                'created_at': str(self.created_at) if self.created_at else ''
            }
        except Exception as e:
            print(f"Error converting to dict: {e}")
            return {
                'id': 0,
                'boy_name': '',
                'girl_name': '',
                'boy_mobile': '',
                'girl_mobile': '',
                'boy_age': 0,
                'girl_age': 0,
                'anniversary_date': '',
                'boy_id': '',
                'girl_id': '',
                'chat_password': '',
                'created_at': ''
            }
    
    @staticmethod
    def get_couple_by_id(couple_id):
        """Get couple by ID"""
        try:
            return Couple.query.get(int(couple_id))
        except:
            return None
    
    def update_anniversary(self, new_date):
        """Update anniversary date"""
        try:
            self.anniversary_date = str(new_date)
            db.session.commit()
            return True
        except:
            return False
    
    def __repr__(self):
        """String representation of the couple"""
        return f"<Couple {self.boy_name} ❤️ {self.girl_name}>"


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)  # 'boy' or 'girl'
    receiver_name = db.Column(db.String(100), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # 'chat' or message types like 'romantic', 'funny', etc.
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define AI message types constant
    AI_MESSAGE_TYPES = ['romantic', 'funny', 'missing', 'good_morning', 'good_night', 
                        'appreciation', 'anniversary', 'sorry', 'custom', 'general']
    
    def __repr__(self):
        return f"<ChatHistory {self.id}: {self.message_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'couple_id': self.couple_id,
            'sender_name': self.sender_name,
            'sender_type': self.sender_type,
            'receiver_name': self.receiver_name,
            'message_type': self.message_type,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'formatted_date': self.created_at.strftime('%B %d, %Y'),
            'formatted_time': self.created_at.strftime('%I:%M %p')
        }
    
    @staticmethod
    def get_ai_messages(session_id=None):
        """Get only AI-generated messages (not person-to-person chat)"""
        query = ChatHistory.query.filter(ChatHistory.message_type.in_(ChatHistory.AI_MESSAGE_TYPES))
        if session_id:
            query = query.filter(ChatHistory.session_id == session_id)
        return query.order_by(ChatHistory.created_at.asc()).all()
    
    @staticmethod
    def get_chat_messages(session_id=None):
        """Get only person-to-person chat messages"""
        query = ChatHistory.query.filter_by(message_type='chat')
        if session_id:
            query = query.filter(ChatHistory.session_id == session_id)
        return query.order_by(ChatHistory.created_at.asc()).all()
    
    @staticmethod
    def get_all_messages_by_type(message_type, limit=100):
        """Get all messages of a specific type"""
        return ChatHistory.query.filter_by(message_type=message_type)\
            .order_by(ChatHistory.created_at.desc())\
            .limit(limit).all()
    
    @staticmethod
    def get_message_stats():
        """Get message statistics for admin dashboard"""
        total = ChatHistory.query.count()
        chat_count = ChatHistory.query.filter_by(message_type='chat').count()
        ai_count = ChatHistory.query.filter(
            ChatHistory.message_type.in_(ChatHistory.AI_MESSAGE_TYPES)
        ).count()
        
        # Count by specific type
        type_counts = {}
        for msg_type in ChatHistory.AI_MESSAGE_TYPES + ['chat']:
            count = ChatHistory.query.filter_by(message_type=msg_type).count()
            if count > 0:
                type_counts[msg_type] = count
        
        # Count messages by sender type
        boy_messages = ChatHistory.query.filter_by(sender_type='boy').count()
        girl_messages = ChatHistory.query.filter_by(sender_type='girl').count()
        
        # Get recent activity (last 7 days)
        week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_messages = ChatHistory.query.filter(
            ChatHistory.created_at >= week_ago
        ).count()
        
        return {
            'total': total,
            'chat_messages': chat_count,
            'ai_messages': ai_count,
            'other': total - chat_count - ai_count,
            'by_type': type_counts,
            'by_sender': {
                'boy': boy_messages,
                'girl': girl_messages
            },
            'recent_7d': recent_messages
        }
    
    @staticmethod
    def search_messages(search_term, limit=100):
        """Search messages by content, sender, or receiver"""
        if not search_term:
            return []
        
        search_pattern = f"%{search_term}%"
        return ChatHistory.query.filter(
            (ChatHistory.message.contains(search_term)) |
            (ChatHistory.sender_name.contains(search_term)) |
            (ChatHistory.receiver_name.contains(search_term))
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_session_messages_by_type(session_id, include_chat=True, include_ai=True):
        """Get messages from a session with filtering options"""
        query = ChatHistory.query.filter_by(session_id=session_id)
        
        if not include_chat and not include_ai:
            return []
        
        if include_chat and not include_ai:
            query = query.filter_by(message_type='chat')
        elif include_ai and not include_chat:
            query = query.filter(ChatHistory.message_type.in_(ChatHistory.AI_MESSAGE_TYPES))
        
        return query.order_by(ChatHistory.created_at.asc()).all()


class Message(db.Model):
    """AI Chat messages model - Kept for backward compatibility"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)  # 'boy' or 'girl'
    sender_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Message {self.id}: {self.sender_name}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'sender_type': self.sender_type,
            'sender_name': self.sender_name,
            'message': self.message,
            'response': self.response,
            'timestamp': self.timestamp.isoformat(),
            'formatted_time': self.timestamp.strftime('%I:%M %p'),
            'formatted_date': self.timestamp.strftime('%B %d, %Y')
        }


class Notification(db.Model):
    """Notifications model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    user_type = db.Column(db.String(10), nullable=False)  # 'boy', 'girl', or 'both'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    icon = db.Column(db.String(50), default='fa-bell')
    color = db.Column(db.String(20), default='primary')
    
    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'user_type': self.user_type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'formatted_time': self.created_at.strftime('%I:%M %p'),
            'formatted_date': self.created_at.strftime('%B %d, %Y'),
            'time_ago': self.get_time_ago(),
            'icon': self.icon,
            'color': self.color
        }
    
    def get_time_ago(self):
        """Get human readable time ago"""
        now = datetime.utcnow()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds // 3600 > 0:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds // 60 > 0:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"