from database import db, Notification
from datetime import datetime

class NotificationManager:
    """Manager for handling notifications"""
    
    def __init__(self):
        self.notification_types = {
            'welcome': {'icon': 'fa-heart', 'color': 'primary'},
            'message': {'icon': 'fa-envelope', 'color': 'info'},
            'anniversary': {'icon': 'fa-calendar-heart', 'color': 'success'},
            'login': {'icon': 'fa-sign-in-alt', 'color': 'success'},
            'reminder': {'icon': 'fa-bell', 'color': 'warning'},
            'achievement': {'icon': 'fa-trophy', 'color': 'success'},
            'tip': {'icon': 'fa-lightbulb', 'color': 'info'}
        }
    
    def create_notification(self, user_id, user_type, title, message, icon=None, color=None):
        """Create a new notification"""
        try:
            # Determine notification type from title
            notification_type = self._determine_type(title)
            
            notification = Notification(
                couple_id=user_id,
                user_type=user_type,
                title=title,
                message=message,
                icon=icon or self.notification_types.get(notification_type, {}).get('icon', 'fa-bell'),
                color=color or self.notification_types.get(notification_type, {}).get('color', 'primary')
            )
            
            db.session.add(notification)
            db.session.commit()
            
            print(f"✅ Notification created for user {user_id}: {title}")
            return notification
            
        except Exception as e:
            print(f"❌ Error creating notification: {str(e)}")
            db.session.rollback()
            return None
    
    def create_bulk_notifications(self, notifications):
        """Create multiple notifications at once"""
        try:
            for notif in notifications:
                notification = Notification(
                    couple_id=notif['user_id'],
                    user_type=notif['user_type'],
                    title=notif['title'],
                    message=notif['message'],
                    icon=notif.get('icon'),
                    color=notif.get('color')
                )
                db.session.add(notification)
            
            db.session.commit()
            print(f"✅ Created {len(notifications)} notifications")
            return True
            
        except Exception as e:
            print(f"❌ Error creating bulk notifications: {str(e)}")
            db.session.rollback()
            return False
    
    def get_notifications(self, user_id, user_type, unread_only=False, limit=20):
        """Get notifications for a user"""
        try:
            query = Notification.query.filter(
                (Notification.couple_id == user_id) & 
                ((Notification.user_type == user_type) | (Notification.user_type == 'both'))
            )
            
            if unread_only:
                query = query.filter_by(is_read=False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            
            return [n.to_dict() for n in notifications]
            
        except Exception as e:
            print(f"❌ Error getting notifications: {str(e)}")
            return []
    
    def mark_as_read(self, notification_ids, user_id, user_type):
        """Mark specific notifications as read"""
        try:
            Notification.query.filter(
                Notification.id.in_(notification_ids),
                Notification.couple_id == user_id,
                (Notification.user_type == user_type) | (Notification.user_type == 'both')
            ).update({Notification.is_read: True}, synchronize_session=False)
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error marking notifications as read: {str(e)}")
            db.session.rollback()
            return False
    
    def mark_all_as_read(self, user_id, user_type):
        """Mark all notifications as read for a user"""
        try:
            Notification.query.filter(
                Notification.couple_id == user_id,
                (Notification.user_type == user_type) | (Notification.user_type == 'both'),
                Notification.is_read == False
            ).update({Notification.is_read: True}, synchronize_session=False)
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error marking all notifications as read: {str(e)}")
            db.session.rollback()
            return False
    
    def get_unread_count(self, user_id, user_type):
        """Get count of unread notifications"""
        try:
            count = Notification.query.filter(
                Notification.couple_id == user_id,
                (Notification.user_type == user_type) | (Notification.user_type == 'both'),
                Notification.is_read == False
            ).count()
            
            return count
            
        except Exception as e:
            print(f"❌ Error getting unread count: {str(e)}")
            return 0
    
    def clear_all_notifications(self, user_id, user_type):
        """Delete all notifications for a user"""
        try:
            Notification.query.filter(
                Notification.couple_id == user_id,
                (Notification.user_type == user_type) | (Notification.user_type == 'both')
            ).delete()
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")
            db.session.rollback()
            return False
    
    def _determine_type(self, title):
        """Determine notification type from title"""
        title_lower = title.lower()
        
        if 'welcome' in title_lower:
            return 'welcome'
        elif 'message' in title_lower or 'chat' in title_lower:
            return 'message'
        elif 'anniversary' in title_lower:
            return 'anniversary'
        elif 'login' in title_lower or 'logged' in title_lower:
            return 'login'
        elif 'tip' in title_lower or 'idea' in title_lower:
            return 'tip'
        elif 'achievement' in title_lower or 'milestone' in title_lower:
            return 'achievement'
        else:
            return 'reminder'