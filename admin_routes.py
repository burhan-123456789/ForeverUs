# admin_routes.py
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from database import db, Couple, Message, ChatHistory, ChatSession, Notification
from datetime import datetime, timedelta
import json

# Change blueprint name to 'admin_panel' to avoid conflict with Flask-Admin
admin_bp = Blueprint('admin_panel', __name__, url_prefix='/admin-panel')

# Admin credentials
ADMIN_USERNAME = "foreverus_admin"
ADMIN_PASSWORD = "ForeverUs@2024"
ADMIN_ID = "FOREVERUS2024"  # Special admin ID that works for both boy and girl login

def admin_required(f):
    """Decorator to check if user is logged in as admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_panel.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_id'] = ADMIN_ID
            return redirect(url_for('admin_panel.dashboard'))
        else:
            return render_template('admin/login.html', error="Invalid credentials")
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('is_admin', None)
    session.pop('admin_id', None)
    return redirect(url_for('admin_panel.login'))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    # Get statistics
    total_couples = Couple.query.count()
    total_messages = Message.query.count()
    total_chat_messages = ChatHistory.query.count()
    total_notifications = Notification.query.count()
    
    # Recent registrations (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_couples = Couple.query.filter(Couple.created_at >= week_ago).count()
    
    # Active couples (those who have sent messages in last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_couples = db.session.query(ChatHistory.couple_id).distinct()\
        .filter(ChatHistory.created_at >= month_ago).count()
    
    # Daily registrations for chart
    daily_registrations = []
    for i in range(7):
        date = datetime.utcnow().date() - timedelta(days=i)
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        count = Couple.query.filter(Couple.created_at >= start, Couple.created_at <= end).count()
        daily_registrations.append({
            'date': date.strftime('%b %d'),
            'count': count
        })
    daily_registrations.reverse()
    
    # Recent couples
    recent_couples_list = Couple.query.order_by(Couple.created_at.desc()).limit(10).all()
    
    stats = {
        'total_couples': total_couples,
        'total_messages': total_messages,
        'total_chat_messages': total_chat_messages,
        'total_notifications': total_notifications,
        'recent_couples': recent_couples,
        'active_couples': active_couples,
        'daily_registrations': daily_registrations
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_couples=recent_couples_list)

@admin_bp.route('/couples')
@admin_required
def couples():
    """Manage couples"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    if search:
        couples = Couple.query.filter(
            (Couple.boy_name.contains(search)) |
            (Couple.girl_name.contains(search)) |
            (Couple.boy_id.contains(search)) |
            (Couple.girl_id.contains(search)) |
            (Couple.boy_mobile.contains(search)) |
            (Couple.girl_mobile.contains(search))
        ).order_by(Couple.created_at.desc()).paginate(page=page, per_page=per_page)
    else:
        couples = Couple.query.order_by(Couple.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/couples.html', couples=couples, search=search)

@admin_bp.route('/couple/<int:couple_id>')
@admin_required
def couple_detail(couple_id):
    """View couple details"""
    couple = Couple.query.get_or_404(couple_id)
    
    # Get AI messages
    ai_messages = Message.query.filter_by(couple_id=couple_id).order_by(Message.timestamp.desc()).limit(50).all()
    
    # Get chat sessions and messages
    chat_sessions = ChatSession.query.filter_by(couple_id=couple_id).order_by(ChatSession.updated_at.desc()).all()
    
    # Get notifications
    boy_notifications = Notification.query.filter_by(couple_id=couple_id, user_type='boy')\
        .order_by(Notification.created_at.desc()).limit(20).all()
    girl_notifications = Notification.query.filter_by(couple_id=couple_id, user_type='girl')\
        .order_by(Notification.created_at.desc()).limit(20).all()
    
    return render_template('admin/couple_detail.html',
                         couple=couple,
                         ai_messages=ai_messages,
                         chat_sessions=chat_sessions,
                         boy_notifications=boy_notifications,
                         girl_notifications=girl_notifications)

@admin_bp.route('/couple/<int:couple_id>/delete', methods=['POST'])
@admin_required
def delete_couple(couple_id):
    """Delete a couple and all associated data"""
    couple = Couple.query.get_or_404(couple_id)
    
    # Delete all associated data
    Message.query.filter_by(couple_id=couple_id).delete()
    ChatHistory.query.filter_by(couple_id=couple_id).delete()
    ChatSession.query.filter_by(couple_id=couple_id).delete()
    Notification.query.filter_by(couple_id=couple_id).delete()
    
    # Delete the couple
    db.session.delete(couple)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Couple deleted successfully'})

@admin_bp.route('/couple/<int:couple_id>/reset-password', methods=['POST'])
@admin_required
def reset_couple_password(couple_id):
    """Reset couple's chat password"""
    couple = Couple.query.get_or_404(couple_id)
    data = request.get_json()
    
    new_password = data.get('password')
    if not new_password or len(new_password) < 4:
        return jsonify({'success': False, 'error': 'Password must be at least 4 characters'}), 400
    
    couple.chat_password = new_password
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password reset successfully'})

@admin_bp.route('/chat-messages')
@admin_required
def chat_messages():
    """View all person-to-person chat messages"""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    search = request.args.get('search', '')
    
    # Debug: Check what's in the database
    total_all = ChatHistory.query.count()
    total_chat = ChatHistory.query.filter_by(message_type='chat').count()
    total_ai = ChatHistory.query.filter(ChatHistory.message_type != 'chat').count()
    
    print(f"=== CHAT MESSAGES DEBUG ===")
    print(f"Total messages in database: {total_all}")
    print(f"Messages with type='chat': {total_chat}")
    print(f"Messages with other types: {total_ai}")
    
    # Get all distinct message types to verify
    types = db.session.query(ChatHistory.message_type).distinct().all()
    print(f"All message types found: {[t[0] for t in types]}")
    
    # Show last 5 messages (any type) to see what's being saved
    last_messages = ChatHistory.query.order_by(ChatHistory.created_at.desc()).limit(5).all()
    for msg in last_messages:
        print(f"ID: {msg.id}, Type: '{msg.message_type}', Sender: {msg.sender_name}, Message: {msg.message[:50]}")
    
    # FIX: Get ALL messages that are NOT AI messages (any type except the AI message types)
    # Instead of filtering only by 'chat', exclude all AI message types
    ai_message_types = ['romantic', 'funny', 'missing', 'good_morning', 'good_night', 'appreciation', 'anniversary', 'sorry', 'custom', 'general']
    
    query = ChatHistory.query.filter(~ChatHistory.message_type.in_(ai_message_types))
    
    # Alternative: If you want only 'chat' type, use this:
    # query = ChatHistory.query.filter_by(message_type='chat')
    
    if search:
        query = query.filter(
            (ChatHistory.message.contains(search)) |
            (ChatHistory.sender_name.contains(search)) |
            (ChatHistory.receiver_name.contains(search))
        )
    
    messages = query.order_by(ChatHistory.created_at.desc()).paginate(page=page, per_page=per_page)
    
    print(f"Messages found in this query: {messages.total}")
    print(f"============================")
    
    return render_template('admin/chat_messages.html', messages=messages, search=search)

# Replace the messages() function in admin_routes.py

@admin_bp.route('/messages')
@admin_required
def messages():
    """View all AI generated messages"""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    search = request.args.get('search', '')
    message_type = request.args.get('type', '')
    
    # FIX: Get messages from ChatHistory model, not Message model
    # AI messages are stored in ChatHistory with message_type values like 'romantic', 'funny', etc.
    ai_message_types = ['romantic', 'funny', 'missing', 'good_morning', 'good_night', 'appreciation', 'anniversary', 'sorry', 'custom', 'general']
    
    query = ChatHistory.query.filter(ChatHistory.message_type.in_(ai_message_types))
    
    if search:
        query = query.filter(
            (ChatHistory.message.contains(search)) |
            (ChatHistory.sender_name.contains(search)) |
            (ChatHistory.receiver_name.contains(search))
        )
    
    if message_type:
        query = query.filter_by(message_type=message_type)
    
    messages = query.order_by(ChatHistory.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Also get Message model data for backward compatibility (if any exists)
    old_messages = []
    if message_type == '' or message_type == 'old':
        old_messages_query = Message.query
        if search:
            old_messages_query = old_messages_query.filter(
                (Message.message.contains(search)) |
                (Message.response.contains(search)) |
                (Message.sender_name.contains(search))
            )
        old_messages = old_messages_query.order_by(Message.timestamp.desc()).all()
    
    return render_template('admin/messages.html', 
                         messages=messages, 
                         search=search, 
                         message_type=message_type,
                         old_messages=old_messages)

@admin_bp.route('/notifications')
@admin_required
def notifications():
    """View all notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    notifications_list = Notification.query.order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page)
    
    return render_template('admin/notifications.html', notifications=notifications_list)

@admin_bp.route('/send-notification', methods=['POST'])
@admin_required
def send_notification():
    """Send a notification to all users"""
    data = request.get_json()
    
    title = data.get('title')
    message = data.get('message')
    user_type = data.get('user_type')  # 'all', 'boy', 'girl'
    
    if not title or not message:
        return jsonify({'success': False, 'error': 'Title and message required'}), 400
    
    if user_type == 'all':
        couples = Couple.query.all()
        for couple in couples:
            # Send to boy
            notification = Notification(
                couple_id=couple.id,
                user_type='boy',
                title=title,
                message=message
            )
            db.session.add(notification)
            
            # Send to girl
            notification = Notification(
                couple_id=couple.id,
                user_type='girl',
                title=title,
                message=message
            )
            db.session.add(notification)
    else:
        couples = Couple.query.all()
        for couple in couples:
            notification = Notification(
                couple_id=couple.id,
                user_type=user_type,
                title=title,
                message=message
            )
            db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Notification sent to {len(couples)} users'})

@admin_bp.route('/stats')
@admin_required
def stats():
    """Advanced statistics page"""
    # Get statistics by date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Registration by day
    registrations = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        count = Couple.query.filter(Couple.created_at >= start, Couple.created_at <= end).count()
        registrations.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    registrations.reverse()
    
    # Messages by day
    messages_by_day = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        ai_count = Message.query.filter(Message.timestamp >= start, Message.timestamp <= end).count()
        chat_count = ChatHistory.query.filter(
            ChatHistory.created_at >= start, 
            ChatHistory.created_at <= end,
            ChatHistory.message_type == 'chat'
        ).count()
        messages_by_day.append({
            'date': date.strftime('%Y-%m-%d'),
            'ai_messages': ai_count,
            'chat_messages': chat_count
        })
    messages_by_day.reverse()
    
    # Top couples by message count
    top_couples = db.session.query(
        ChatHistory.couple_id,
        db.func.count(ChatHistory.id).label('message_count')
    ).filter(ChatHistory.message_type == 'chat')\
     .group_by(ChatHistory.couple_id)\
     .order_by(db.desc('message_count'))\
     .limit(10).all()
    
    top_couples_data = []
    for couple_id, count in top_couples:
        couple = Couple.query.get(couple_id)
        if couple:
            top_couples_data.append({
                'boy_name': couple.boy_name,
                'girl_name': couple.girl_name,
                'boy_id': couple.boy_id,
                'girl_id': couple.girl_id,
                'message_count': count
            })
    
    return render_template('admin/stats.html',
                         registrations=registrations,
                         messages_by_day=messages_by_day,
                         top_couples=top_couples_data,
                         days=days)