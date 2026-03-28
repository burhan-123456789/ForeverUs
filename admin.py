from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, url_for, request
from functools import wraps
from config import Config

# Import all models
from database import Couple, Message, Notification, ChatSession, ChatHistory

class AdminModelView(ModelView):
    """Base ModelView for admin panel"""
    
    def is_accessible(self):
        """Check if user is authenticated for admin access"""
        # Simple authentication - in production, use proper authentication
        auth = request.authorization
        if auth and auth.username == Config.ADMIN_USERNAME and auth.password == Config.ADMIN_PASSWORD:
            return True
        return False
    
    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login page when not authenticated"""
        return redirect(url_for('index'))


class CoupleAdmin(AdminModelView):
    """Admin view for Couple model"""
    column_list = ['id', 'boy_name', 'girl_name', 'boy_id', 'girl_id', 'created_at']
    column_searchable_list = ['boy_name', 'girl_name', 'boy_id', 'girl_id', 'boy_mobile', 'girl_mobile']
    column_filters = ['boy_age', 'girl_age', 'created_at']
    column_editable_list = ['boy_name', 'girl_name', 'anniversary_date']
    form_columns = ['boy_name', 'girl_name', 'boy_mobile', 'girl_mobile', 'boy_age', 'girl_age', 'anniversary_date']
    
    def __init__(self, session, **kwargs):
        super(CoupleAdmin, self).__init__(Couple, session, **kwargs)


class MessageAdmin(AdminModelView):
    """Admin view for Message model"""
    column_list = ['id', 'couple_id', 'sender_name', 'sender_type', 'message', 'response', 'timestamp']
    column_searchable_list = ['sender_name', 'message', 'response']
    column_filters = ['sender_type', 'timestamp']
    column_editable_list = []
    form_columns = ['couple_id', 'sender_type', 'sender_name', 'message', 'response']
    
    def __init__(self, session, **kwargs):
        super(MessageAdmin, self).__init__(Message, session, **kwargs)


class NotificationAdmin(AdminModelView):
    """Admin view for Notification model"""
    column_list = ['id', 'couple_id', 'user_type', 'title', 'is_read', 'created_at']
    column_searchable_list = ['title', 'message']
    column_filters = ['user_type', 'is_read', 'created_at']
    column_editable_list = ['is_read']
    form_columns = ['couple_id', 'user_type', 'title', 'message', 'is_read', 'icon', 'color']
    
    def __init__(self, session, **kwargs):
        super(NotificationAdmin, self).__init__(Notification, session, **kwargs)


class ChatSessionAdmin(AdminModelView):
    """Admin view for ChatSession model"""
    column_list = ['id', 'session_uuid', 'couple_id', 'title', 'created_at', 'updated_at']
    column_searchable_list = ['title', 'session_uuid']
    column_filters = ['created_at', 'updated_at']
    column_editable_list = ['title']
    form_columns = ['couple_id', 'title']
    
    def __init__(self, session, **kwargs):
        super(ChatSessionAdmin, self).__init__(ChatSession, session, **kwargs)


class ChatHistoryAdmin(AdminModelView):
    """Admin view for ChatHistory model"""
    column_list = ['id', 'session_id', 'couple_id', 'sender_name', 'sender_type', 'message_type', 'created_at']
    column_searchable_list = ['sender_name', 'message']
    column_filters = ['sender_type', 'message_type', 'created_at']
    column_editable_list = []
    form_columns = ['session_id', 'couple_id', 'sender_name', 'sender_type', 'receiver_name', 'message_type', 'message']
    
    def __init__(self, session, **kwargs):
        super(ChatHistoryAdmin, self).__init__(ChatHistory, session, **kwargs)


def init_admin(app, db):
    """Initialize Flask-Admin with all models"""
    # Remove template_mode parameter
    admin = Admin(app, name='ForeverUs Admin')
    
    # Add views
    admin.add_view(CoupleAdmin(db.session, name='Couples', endpoint='admin_couples'))
    admin.add_view(MessageAdmin(db.session, name='AI Messages', endpoint='admin_messages'))
    admin.add_view(NotificationAdmin(db.session, name='Notifications', endpoint='admin_notifications'))
    admin.add_view(ChatSessionAdmin(db.session, name='Chat Sessions', endpoint='admin_chat_sessions'))
    admin.add_view(ChatHistoryAdmin(db.session, name='Chat History', endpoint='admin_chat_history'))
    
    print("✅ Flask-Admin initialized")
    return admin