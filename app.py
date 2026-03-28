from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from config import Config
from database import db, Couple, ChatHistory, ChatSession, Notification, Message
from datetime import datetime, timedelta
import os
import time
import json
from huggingface_manager import init_huggingface_manager, get_huggingface_model, key_manager
import traceback
import uuid
from admin import init_admin
from chat_manager import ChatManager
from notification_manager import NotificationManager
from admin_routes import admin_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Initialize Flask-Admin
admin = init_admin(app, db)
app.register_blueprint(admin_bp)

# Global references
key_manager = None
chat_manager = None
notification_manager = None

# Initialize Hugging Face with single key
print("=" * 50)
print("🚀 Starting ForeverUs Application")
print("=" * 50)
print("📝 Configuring Hugging Face...")

# Check for single API key first, then fall back to multiple keys for backward compatibility
api_key = app.config.get('HUGGINGFACE_API_KEY')
if not api_key and app.config.get('HUGGINGFACE_API_KEYS'):
    # Fall back to first key from the list
    api_keys = app.config.get('HUGGINGFACE_API_KEYS', [])
    api_key = api_keys[0] if api_keys else None

if api_key:
    try:
        api_key = str(api_key).strip()
        
        if api_key:
            print(f"✅ Found valid API key: {api_key[:10]}...")
            # Initialize the key manager with single key
            key_manager = init_huggingface_manager([api_key], app.config['HUGGINGFACE_MODEL'])
            print(f"✅ Hugging Face initialized successfully")
            print(f"📊 Model: {app.config['HUGGINGFACE_MODEL']}")
            print(f"😊 Emoji support enabled for all messages")
            
            # Initialize chat manager
            chat_manager = ChatManager(key_manager)
            
            # Initialize notification manager
            notification_manager = NotificationManager()
            
            # Test if key manager is working
            if key_manager:
                stats = key_manager.get_stats()
                # Check which format the stats are in and display accordingly
                if 'available_keys' in stats:
                    # Multiple keys format
                    print(f"📊 Key Manager Stats: {stats['available_keys']}/{stats['total_keys']} keys available")
                else:
                    # Single key format
                    print(f"📊 Key Manager Stats: {stats['successful_uses']} successful, {stats['failed_uses']} failed")
                    print(f"📊 Key available: {stats['available']}")
                    if not stats['available'] and stats.get('cooldown_remaining', 0) > 0:
                        print(f"📊 Cooldown: {stats['cooldown_remaining']}s remaining")
            else:
                print("❌ Key manager returned None")
        else:
            print("⚠️ No valid API key found")
            print("📝 Please check your .env file and ensure HUGGINGFACE_API_KEY is correctly set")
            key_manager = None
            chat_manager = None
            notification_manager = NotificationManager()
    except Exception as e:
        print(f"❌ Error initializing Hugging Face: {str(e)}")
        traceback.print_exc()
        key_manager = None
        chat_manager = None
        notification_manager = NotificationManager()
else:
    print("⚠️ No Hugging Face API key found in config")
    print("📝 Please set HUGGINGFACE_API_KEY in .env file")
    key_manager = None
    chat_manager = None
    notification_manager = NotificationManager()

print("=" * 50)

# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database tables created/verified")

# Store active chat sessions for polling
active_chat_sessions = {}

@app.route('/')
def index():
    """Render the main landing page"""
    # If user is already logged in, redirect to dashboard
    if session.get('user_id') and session.get('user_type'):
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register')
def register_page():
    """Render registration page"""
    return render_template('register.html')

@app.route('/chat')
def chat_page():
    """Render couple chat page with password protection"""
    # Check if user is logged in
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id or not user_type:
        return redirect(url_for('index'))
    
    # Fetch couple from database
    couple = db.session.get(Couple, user_id)
    if not couple:
        session.clear()
        return redirect(url_for('index'))
    
    # Check if chat is unlocked in this session
    chat_unlocked = session.get('chat_unlocked', False)
    
    # Convert couple to dictionary
    couple_dict = {
        'id': couple.id,
        'boy_name': couple.boy_name,
        'girl_name': couple.girl_name,
        'boy_id': couple.boy_id,
        'girl_id': couple.girl_id
    }
    
    # Create a user dictionary with necessary info
    user_dict = {
        'id': user_id,
        'type': user_type,
        'name': couple.boy_name if user_type == 'boy' else couple.girl_name
    }
    
    return render_template('chat.html', 
                         couple=couple_dict, 
                         user_type=user_type,
                         user=user_dict, 
                         chat_unlocked=chat_unlocked)

@app.route('/api/chat/mark-seen', methods=['POST'])
def mark_messages_seen():
    """Mark messages as seen by the user"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        data = request.get_json()
        if not data or 'message_ids' not in data or 'session_id' not in data:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Message IDs and session ID are required'
            }), 400
        
        message_ids = data['message_ids']
        session_id = data['session_id']
        
        if not message_ids:
            return jsonify({
                'success': True,
                'message': 'No messages to mark as seen'
            })
        # TODO:
        
        return jsonify({
            'success': True,
            'message': f'Marked {len(message_ids)} messages as seen'
        })
        
    except Exception as e:
        print(f"Error marking messages as seen: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to mark messages as seen'
        }), 500
    
@app.route('/offline')
def offline():
    """Render offline page"""
    return render_template('offline.html')

@app.route('/dashboard')
def dashboard():
    """Render dashboard page with message generator interface"""
    # Check if user is logged in
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id or not user_type:
        return redirect(url_for('index'))
    
    # Fetch couple from database
    couple = db.session.get(Couple, user_id)
    if not couple:
        session.clear()
        return redirect(url_for('index'))
    
    # Calculate days until anniversary
    days_until = 0
    try:
        anniversary = datetime.strptime(couple.anniversary_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        next_anniversary = anniversary.replace(year=today.year)
        
        if next_anniversary < today:
            next_anniversary = next_anniversary.replace(year=today.year + 1)
        
        days_until = (next_anniversary - today).days
    except:
        days_until = 0
    
    # Convert couple to dictionary for JSON serialization
    couple_dict = {
        'id': couple.id,
        'boy_name': couple.boy_name,
        'girl_name': couple.girl_name,
        'boy_mobile': couple.boy_mobile,
        'girl_mobile': couple.girl_mobile,
        'boy_age': couple.boy_age,
        'girl_age': couple.girl_age,
        'anniversary_date': couple.anniversary_date,
        'boy_id': couple.boy_id,
        'girl_id': couple.girl_id,
        'created_at': couple.created_at.isoformat() if couple.created_at else None
    }
    
    return render_template('dashboard.html', 
                         couple=couple_dict, 
                         user_type=user_type,
                         days_until=days_until)

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new couple with chat password"""
    try:
        data = request.get_json()
        
        # Log received data for debugging (remove in production)
        print(f"Registration data received: {data}")
        
        # Validate required fields
        required_fields = ['boy_name', 'girl_name', 'boy_mobile', 'girl_mobile', 
                          'boy_age', 'girl_age', 'anniversary_date', 'chat_password']
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif data[field] is None or str(data[field]).strip() == '':
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate password length
        chat_password = str(data['chat_password']).strip()
        if len(chat_password) < 4:
            return jsonify({
                'success': False,
                'error': 'invalid_password',
                'message': 'Chat password must be at least 4 characters long'
            }), 400
        
        # Validate mobile numbers (10 digits)
        boy_mobile = str(data['boy_mobile']).strip()
        girl_mobile = str(data['girl_mobile']).strip()
        
        if not boy_mobile.isdigit() or len(boy_mobile) != 10:
            return jsonify({
                'success': False,
                'error': 'invalid_mobile',
                'message': 'Boy\'s mobile number must be 10 digits'
            }), 400
            
        if not girl_mobile.isdigit() or len(girl_mobile) != 10:
            return jsonify({
                'success': False,
                'error': 'invalid_mobile',
                'message': 'Girl\'s mobile number must be 10 digits'
            }), 400
        
        # Validate ages
        try:
            boy_age = int(data['boy_age'])
            girl_age = int(data['girl_age'])
            
            if boy_age < 18 or boy_age > 120:
                return jsonify({
                    'success': False,
                    'error': 'invalid_age',
                    'message': 'Boy\'s age must be between 18 and 120'
                }), 400
                
            if girl_age < 18 or girl_age > 120:
                return jsonify({
                    'success': False,
                    'error': 'invalid_age',
                    'message': 'Girl\'s age must be between 18 and 120'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'invalid_age',
                'message': 'Age must be a valid number'
            }), 400
        
        # Validate anniversary date
        try:
            from datetime import datetime
            anniversary_date = data['anniversary_date']
            datetime.strptime(anniversary_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'invalid_date',
                'message': 'Invalid anniversary date format. Use YYYY-MM-DD'
            }), 400
        
        # Check for duplicate entry with same names and mobile numbers
        existing_couple = Couple.query.filter(
            (Couple.boy_name == data['boy_name']) & 
            (Couple.girl_name == data['girl_name']) &
            (Couple.boy_mobile == boy_mobile) & 
            (Couple.girl_mobile == girl_mobile)
        ).first()
        
        if existing_couple:
            if existing_couple.anniversary_date == anniversary_date:
                return jsonify({
                    'success': False,
                    'error': 'duplicate_entry',
                    'message': 'An account with these details already exists! Please use the login page.',
                    'existing_ids': {
                        'boy_id': existing_couple.boy_id,
                        'girl_id': existing_couple.girl_id
                    }
                }), 409
            else:
                return jsonify({
                    'success': False,
                    'error': 'duplicate_names',
                    'message': 'This couple already has an account. Please use the login page.',
                    'existing_ids': {
                        'boy_id': existing_couple.boy_id,
                        'girl_id': existing_couple.girl_id
                    }
                }), 409
        
        # Check for duplicate mobile numbers
        existing_mobile = Couple.query.filter(
            (Couple.boy_mobile == boy_mobile) | 
            (Couple.girl_mobile == girl_mobile)
        ).first()
        
        if existing_mobile:
            return jsonify({
                'success': False,
                'error': 'duplicate_mobile',
                'message': 'A user with this mobile number already exists. Please use different mobile numbers or login.'
            }), 409
        
        # Create new couple with password
        couple = Couple(
            boy_name=data['boy_name'],
            girl_name=data['girl_name'],
            boy_mobile=boy_mobile,
            girl_mobile=girl_mobile,
            boy_age=boy_age,
            girl_age=girl_age,
            anniversary_date=anniversary_date,
            chat_password=chat_password
        )
        
        # Generate unique IDs based on individual names
        couple.boy_id = couple.generate_unique_id('boy', couple.boy_name)
        couple.girl_id = couple.generate_unique_id('girl', couple.girl_name)
        
        # Save to database
        db.session.add(couple)
        db.session.commit()
        
        # Create welcome notification
        global notification_manager
        if notification_manager:
            try:
                notification_manager.create_notification(
                    user_id=couple.id,
                    user_type='boy',
                    title='Welcome to ForeverUs! 🎉',
                    message=f'Welcome {couple.boy_name}! Your unique ID is: {couple.boy_id}'
                )
                notification_manager.create_notification(
                    user_id=couple.id,
                    user_type='girl',
                    title='Welcome to ForeverUs! 🎉',
                    message=f'Welcome {couple.girl_name}! Your unique ID is: {couple.girl_id}'
                )
            except Exception as e:
                print(f"Notification creation error (non-critical): {str(e)}")
        
        print(f"✅ New couple registered: {couple.boy_name} & {couple.girl_name} (ID: {couple.id})")
        print(f"   Boy ID: {couple.boy_id} (from {couple.boy_name})")
        print(f"   Girl ID: {couple.girl_id} (from {couple.girl_name})")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'boy_id': couple.boy_id,
            'girl_id': couple.girl_id
        })
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Registration failed. Please try again.'
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user - supports admin ID as well"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'unique_id' not in data or 'user_type' not in data:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Unique ID and user type are required'
            }), 400
        
        unique_id = data['unique_id'].strip().upper()
        user_type = data['user_type']
        
        # Check for admin ID - special case
        if unique_id == "FOREVERUS2024":
            # Admin ID can be used as both boy and girl
            # Create a special admin session
            session['user_id'] = 0  # Special admin ID
            session['user_type'] = user_type
            session['chat_unlocked'] = True
            session['is_admin_user'] = True
            session.permanent = True
            
            return jsonify({
                'success': True,
                'message': 'Admin login successful!',
                'redirect': '/dashboard',
                'is_admin': True
            })
        
        # Regular couple login
        couple = Couple.verify_login(unique_id, user_type)
        
        if couple:
            # Set session
            session['user_id'] = couple.id
            session['user_type'] = user_type
            session['chat_unlocked'] = False  # Chat starts locked
            session['is_admin_user'] = False
            session.permanent = True
            
            # Create login notification
            global notification_manager
            if notification_manager:
                notification_manager.create_notification(
                    user_id=couple.id,
                    user_type=user_type,
                    title='Login Successful ✅',
                    message=f'Welcome back! You have successfully logged in.'
                )
            
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'redirect': '/dashboard'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'invalid_credentials',
                'message': 'Invalid Unique ID. Please check and try again.'
            }), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Login failed. Please try again.'
        }), 500

@app.route('/api/chat/unlock', methods=['POST'])
def unlock_chat():
    """Unlock chat with password"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Password is required'
            }), 400
        
        password = data['password']
        
        # Verify password
        couple = db.session.get(Couple, user_id)
        if not couple:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'User not found'
            }), 404
        
        if couple.chat_password == password:
            # Set unlocked in session
            session['chat_unlocked'] = True
            
            # Get or create a default chat session
            default_session = ChatSession.query.filter_by(couple_id=user_id).order_by(ChatSession.updated_at.desc()).first()
            if not default_session:
                default_session = ChatSession(
                    couple_id=user_id,
                    title=f"{couple.boy_name} & {couple.girl_name}'s Chat"
                )
                db.session.add(default_session)
                db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Chat unlocked successfully',
                'session_id': default_session.id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'invalid_password',
                'message': 'Incorrect password'
            }), 401
            
    except Exception as e:
        print(f"Unlock error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to unlock chat'
        }), 500

# In app.py - Complete send_chat_message function

@app.route('/api/chat/messages', methods=['POST'])
def send_chat_message():
    """Send a real-time chat message to partner"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        chat_unlocked = session.get('chat_unlocked', False)
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        if not chat_unlocked:
            return jsonify({
                'success': False,
                'error': 'chat_locked',
                'message': 'Chat is locked. Please enter password first.'
            }), 403
        
        data = request.get_json()
        if not data or 'message' not in data or 'session_id' not in data:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Message and session ID are required'
            }), 400
        
        message_text = data['message'].strip()
        session_id = data['session_id']
        
        if not message_text:
            return jsonify({
                'success': False,
                'error': 'empty_message',
                'message': 'Message cannot be empty'
            }), 400
        
        # Validate message length
        if len(message_text) > 1000:
            return jsonify({
                'success': False,
                'error': 'message_too_long',
                'message': 'Message cannot exceed 1000 characters'
            }), 400
        
        # Get couple info
        couple = db.session.get(Couple, user_id)
        if not couple:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'User not found'
            }), 404
        
        # Verify session belongs to couple
        chat_session = ChatSession.query.filter_by(id=session_id, couple_id=user_id).first()
        if not chat_session:
            return jsonify({
                'success': False,
                'error': 'invalid_session',
                'message': 'Invalid chat session'
            }), 400
        
        sender_name = couple.boy_name if user_type == 'boy' else couple.girl_name
        receiver_name = couple.girl_name if user_type == 'boy' else couple.boy_name
        
        # Log the message being saved
        print(f"=== SAVING CHAT MESSAGE ===")
        print(f"Session ID: {session_id}")
        print(f"Couple ID: {user_id}")
        print(f"Sender: {sender_name} ({user_type})")
        print(f"Receiver: {receiver_name}")
        print(f"Message Type: 'chat'")
        print(f"Message: {message_text[:100]}")
        
        # Save message to database with message_type='chat'
        chat_message = ChatHistory(
            session_id=session_id,
            couple_id=user_id,
            sender_name=sender_name,
            sender_type=user_type,
            receiver_name=receiver_name,
            message_type='chat',  # IMPORTANT: Always 'chat' for person-to-person
            message=message_text
        )
        db.session.add(chat_message)
        
        # Update session updated_at
        chat_session.updated_at = datetime.utcnow()
        
        # Commit to database
        db.session.commit()
        
        # Verify the save was successful
        saved_message = ChatHistory.query.get(chat_message.id)
        if not saved_message:
            print(f"❌ ERROR: Message not found after save!")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'save_failed',
                'message': 'Failed to save message'
            }), 500
        
        print(f"✅ Message saved successfully with ID: {chat_message.id}")
        print(f"   Message type in DB: '{saved_message.message_type}'")
        print(f"   Created at: {saved_message.created_at}")
        print(f"=========================")
        
        # Update active sessions for polling
        if user_id not in active_chat_sessions:
            active_chat_sessions[user_id] = {
                'last_message_id': chat_message.id,
                'last_check': datetime.utcnow()
            }
        else:
            active_chat_sessions[user_id]['last_message_id'] = chat_message.id
            active_chat_sessions[user_id]['last_check'] = datetime.utcnow()
        
        # Create notification for partner (optional)
        global notification_manager
        if notification_manager:
            try:
                partner_type = 'girl' if user_type == 'boy' else 'boy'
                notification_manager.create_notification(
                    user_id=user_id,
                    user_type=partner_type,
                    title='New Message 💬',
                    message=f'{sender_name} sent you a message',
                    icon='fa-envelope',
                    color='info'
                )
                print(f"✅ Notification sent to {partner_type}")
            except Exception as e:
                print(f"⚠️ Notification creation error (non-critical): {str(e)}")
        
        # Return the message with proper timestamp formatting
        return jsonify({
            'success': True,
            'message': 'Message sent successfully',
            'chat_id': chat_message.id,
            'timestamp': chat_message.created_at.isoformat(),
            'formatted_time': chat_message.created_at.strftime('%I:%M %p'),
            'formatted_date': chat_message.created_at.strftime('%B %d, %Y')
        })
        
    except Exception as e:
        print(f"❌ Send message error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to send message. Please try again.'
        }), 500
    
@app.route('/api/chat/poll', methods=['GET'])
def poll_messages():
    """HTTP polling endpoint for new messages"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        chat_unlocked = session.get('chat_unlocked', False)
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        if not chat_unlocked:
            return jsonify({
                'success': False,
                'error': 'chat_locked',
                'message': 'Chat is locked'
            }), 403
        
        session_id = request.args.get('session_id', type=int)
        last_message_id = request.args.get('last_message_id', 0, type=int)
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Session ID is required'
            }), 400
        
        # Verify session belongs to couple
        chat_session = ChatSession.query.filter_by(id=session_id, couple_id=user_id).first()
        if not chat_session:
            return jsonify({
                'success': False,
                'error': 'invalid_session',
                'message': 'Invalid chat session'
            }), 400
        
        # Get couple info for name mapping
        couple = db.session.get(Couple, user_id)
        
        # Query for new messages - only get 'chat' type messages for the real-time chat
        new_messages = ChatHistory.query.filter(
            ChatHistory.session_id == session_id,
            ChatHistory.id > last_message_id,
            ChatHistory.message_type == 'chat'  # Only get person-to-person chat messages
        ).order_by(ChatHistory.created_at.asc()).all()
        
        messages_data = []
        for msg in new_messages:
            messages_data.append({
                'id': msg.id,
                'message': msg.message,
                'sender_type': msg.sender_type,
                'sender_name': msg.sender_name,
                'receiver_name': msg.receiver_name,
                'created_at': msg.created_at.isoformat(),
                'formatted_time': msg.created_at.strftime('%I:%M %p'),  # Add formatted time
                'is_from_current_user': msg.sender_type == user_type,
                'display_sender_name': 'You' if msg.sender_type == user_type else 
                                      (couple.boy_name if msg.sender_type == 'boy' else couple.girl_name) if couple else msg.sender_name
            })
        
        return jsonify({
            'success': True,
            'messages': messages_data,
            'last_message_id': max([msg.id for msg in new_messages], default=last_message_id)
        })
        
    except Exception as e:
        print(f"Poll error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to poll messages'
        }), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Get chat history for the current user (AI chat - kept for compatibility)"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        limit = request.args.get('limit', 50, type=int)
        
        messages = Message.query.filter_by(couple_id=user_id)\
            .order_by(Message.timestamp.desc())\
            .limit(limit)\
            .all()
        
        messages_data = [{
            'id': msg.id,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_name,
            'message': msg.message,
            'response': msg.response,
            'timestamp': msg.timestamp.isoformat(),
            'formatted_time': msg.timestamp.strftime('%I:%M %p'),
            'formatted_date': msg.timestamp.strftime('%B %d, %Y')
        } for msg in messages]
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        print(f"Error fetching chat history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to fetch chat history'
        }), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notifications for the current user"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        global notification_manager
        if not notification_manager:
            return jsonify({
                'success': False,
                'error': 'service_unavailable',
                'message': 'Notification service unavailable'
            }), 503
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 20, type=int)
        
        notifications = notification_manager.get_notifications(
            user_id=user_id,
            user_type=user_type,
            unread_only=unread_only,
            limit=limit
        )
        
        unread_count = notification_manager.get_unread_count(user_id, user_type)
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count
        })
        
    except Exception as e:
        print(f"Error fetching notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to fetch notifications'
        }), 500

@app.route('/api/notifications/read', methods=['POST'])
def mark_notifications_read():
    """Mark notifications as read"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        data = request.get_json() or {}
        notification_ids = data.get('notification_ids', [])
        
        global notification_manager
        if not notification_manager:
            return jsonify({
                'success': False,
                'error': 'service_unavailable',
                'message': 'Notification service unavailable'
            }), 503
        
        if notification_ids:
            # Mark specific notifications as read
            notification_manager.mark_as_read(notification_ids, user_id, user_type)
        else:
            # Mark all as read
            notification_manager.mark_all_as_read(user_id, user_type)
        
        return jsonify({
            'success': True,
            'message': 'Notifications marked as read'
        })
        
    except Exception as e:
        print(f"Error marking notifications as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to mark notifications as read'
        }), 500

@app.route('/api/notifications/clear', methods=['POST'])
def clear_all_notifications():
    """Clear all notifications for the current user"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        global notification_manager
        if not notification_manager:
            return jsonify({
                'success': False,
                'error': 'service_unavailable',
                'message': 'Notification service unavailable'
            }), 503
        
        notification_manager.clear_all_notifications(user_id, user_type)
        
        return jsonify({
            'success': True,
            'message': 'All notifications cleared'
        })
        
    except Exception as e:
        print(f"Error clearing notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to clear notifications'
        }), 500

@app.route('/api/chat-sessions', methods=['GET'])
def get_chat_sessions():
    """Get all chat sessions for the current user - with AI message counts only"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Get couple info
        couple = db.session.get(Couple, user_id)
        if not couple:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'User not found'
            }), 404
        
        # Get all chat sessions for this couple
        sessions = ChatSession.query.filter_by(couple_id=user_id).order_by(ChatSession.updated_at.desc()).all()
        
        sessions_data = []
        for chat_session in sessions:
            # IMPORTANT FIX: Get ONLY AI messages for this session (exclude 'chat' type)
            messages = ChatHistory.query.filter(
                ChatHistory.session_id == chat_session.id,
                ChatHistory.message_type != 'chat'  # Only count AI messages
            ).order_by(ChatHistory.created_at.asc()).all()
            
            # Count messages by sender (only AI messages)
            user_message_count = 0
            partner_message_count = 0
            last_message = None
            last_message_sender = None
            last_message_time = None
            
            if messages:
                last_msg = messages[-1]
                last_message = last_msg.message[:50] + '...' if len(last_msg.message) > 50 else last_msg.message
                last_message_sender = last_msg.sender_type
                last_message_time = last_msg.created_at.strftime('%I:%M %p')
                
                # Count messages by sender
                for msg in messages:
                    if msg.sender_type == user_type:
                        user_message_count += 1
                    else:
                        partner_message_count += 1
            
            # Get preview from first message or use last message
            preview = last_message if last_message else 'No messages'
            
            sessions_data.append({
                'id': chat_session.id,
                'session_uuid': chat_session.session_uuid,
                'title': chat_session.title,
                'created_at': chat_session.created_at.isoformat(),
                'updated_at': chat_session.updated_at.isoformat(),
                'formatted_date': chat_session.updated_at.strftime('%B %d, %Y'),
                'formatted_time': chat_session.updated_at.strftime('%I:%M %p'),
                'preview': preview,
                'last_message_sender': last_message_sender,
                'last_message_time': last_message_time,
                'user_message_count': user_message_count,
                'partner_message_count': partner_message_count,
                'total_messages': len(messages)
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_data,
            'current_user': user_type
        })
        
    except Exception as e:
        print(f"Error fetching chat sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to fetch chat sessions'
        }), 500

@app.route('/api/chat-sessions', methods=['POST'])
def create_chat_session():
    """Create a new chat session"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        data = request.get_json() or {}
        title = data.get('title', 'New Conversation')
        
        # Create new chat session
        chat_session = ChatSession(
            couple_id=user_id,
            title=title
        )
        db.session.add(chat_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session': {
                'id': chat_session.id,
                'session_uuid': chat_session.session_uuid,
                'title': chat_session.title
            }
        })
        
    except Exception as e:
        print(f"Error creating chat session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to create chat session'
        }), 500

@app.route('/api/chat-sessions/<int:session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get all messages for a specific chat session - FILTERED to show only AI messages in dashboard"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Verify session belongs to user
        chat_session = ChatSession.query.filter_by(id=session_id, couple_id=user_id).first()
        if not chat_session:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'Chat session not found'
            }), 404
        
        # Get couple info for proper name display
        couple = db.session.get(Couple, user_id)
        if not couple:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'User not found'
            }), 404
        
        # IMPORTANT FIX: Get ONLY AI-generated messages for the dashboard
        # Filter out 'chat' type messages which are person-to-person chats
        messages = ChatHistory.query.filter(
            ChatHistory.session_id == session_id,
            ChatHistory.message_type != 'chat'  # Exclude person-to-person chat messages
        ).order_by(ChatHistory.created_at.asc()).all()
        
        messages_data = [{
            'id': msg.id,
            'message_type': msg.message_type,
            'message': msg.message,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_name,
            'receiver_name': msg.receiver_name,
            'created_at': msg.created_at.isoformat(),
            'formatted_time': msg.created_at.strftime('%I:%M %p'),
            'is_from_current_user': msg.sender_type == user_type,
            # Add display name for better UI
            'display_sender_name': 'You' if msg.sender_type == user_type else 
                                  (couple.boy_name if msg.sender_type == 'boy' else couple.girl_name)
        } for msg in messages]
        
        return jsonify({
            'success': True,
            'session': {
                'id': chat_session.id,
                'title': chat_session.title,
                'created_at': chat_session.created_at.isoformat()
            },
            'messages': messages_data,
            'current_user': user_type,
            'couple': {
                'boy_name': couple.boy_name,
                'girl_name': couple.girl_name
            }
        })
        
    except Exception as e:
        print(f"Error fetching session messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to fetch messages'
        }), 500

@app.route('/api/chat-sessions/<int:session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session and all its messages"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Find the session and verify ownership
        chat_session = ChatSession.query.filter_by(id=session_id, couple_id=user_id).first()
        
        if not chat_session:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'Chat session not found'
            }), 404
        
        # Delete the session (cascade will delete all messages)
        db.session.delete(chat_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chat session deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting chat session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to delete chat session'
        }), 500

@app.route('/api/clear-all-sessions', methods=['POST'])
def clear_all_sessions():
    """Clear all chat sessions for the current user"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Delete all sessions for this couple (cascade will delete all messages)
        ChatSession.query.filter_by(couple_id=user_id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All chat sessions cleared'
        })
        
    except Exception as e:
        print(f"Error clearing sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Failed to clear sessions'
        }), 500

# In app.py - Complete generate_message function

@app.route('/api/generate-message', methods=['POST'])
def generate_message():
    """Generate an AI message based on type"""
    global key_manager
    
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Get request data
        data = request.get_json()
        if not data or 'message_type' not in data:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Message type is required'
            }), 400
        
        message_type = data['message_type']
        custom_prompt = data.get('custom_prompt')
        session_id = data.get('session_id')
        
        # Validate message type
        valid_types = ['romantic', 'funny', 'missing', 'good_morning', 'good_night', 
                      'appreciation', 'anniversary', 'sorry', 'custom', 'general']
        
        if message_type not in valid_types:
            return jsonify({
                'success': False,
                'error': 'invalid_type',
                'message': f'Invalid message type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        # Check if key manager is available
        if not key_manager:
            return jsonify({
                'success': False,
                'error': 'ai_service_unavailable',
                'message': 'AI service is currently unavailable. Please try again later.',
                'offline_mode': True
            }), 503
        
        # Fetch couple info for personalization
        couple = db.session.get(Couple, user_id)
        if not couple:
            return jsonify({
                'success': False,
                'error': 'session_expired',
                'message': 'Session expired. Please login again.'
            }), 401
        
        # Get or create chat session
        if session_id:
            # Verify session belongs to user
            chat_session = ChatSession.query.filter_by(id=session_id, couple_id=user_id).first()
            if not chat_session:
                return jsonify({
                    'success': False,
                    'error': 'invalid_session',
                    'message': 'Invalid chat session'
                }), 400
        else:
            # Create new session if none provided
            chat_session = ChatSession(
                couple_id=user_id,
                title=f"New {message_type.replace('_', ' ').title()} Conversation"
            )
            db.session.add(chat_session)
            db.session.commit()
            print(f"✅ Created new chat session: {chat_session.id} - {chat_session.title}")
        
        # Prepare prompt based on message type and user
        sender_name = couple.boy_name if user_type == 'boy' else couple.girl_name
        receiver_name = couple.girl_name if user_type == 'boy' else couple.boy_name
        
        # Anniversary context
        anniversary_context = ""
        try:
            anniversary_date = datetime.strptime(couple.anniversary_date, '%Y-%m-%d')
            today = datetime.now()
            days_since = (today - anniversary_date).days
            if days_since >= 0:
                anniversary_context = f" They have been together for {days_since} days."
        except:
            pass
        
        # If custom prompt is provided, use that
        if custom_prompt and message_type == 'custom':
            prompt = f"{custom_prompt} Write a personal message from {sender_name} to {receiver_name}. Make it heartfelt and genuine. Use appropriate emojis. About 3-4 sentences.{anniversary_context}"
        else:
            # Enhanced prompts with emoji instructions and personalization
            prompts = {
                'romantic': f"Write a romantic message from {sender_name} to {receiver_name}. Make it deeply heartfelt and loving. Include romantic emojis like ❤️ 💕 💖 🌹. Express love and commitment. About 3-4 sentences.{anniversary_context}",
                
                'funny': f"Write a funny and playful message from {sender_name} to {receiver_name} that will make them laugh. Use fun emojis like 😂 🎉 😆 🤪. Keep it light-hearted, cute, and humorous. About 3-4 sentences.{anniversary_context}",
                
                'missing': f"Write a sweet message from {sender_name} to {receiver_name} expressing how much they miss them. Use emotional emojis like 🥺 💫 🌙 💭. Make it emotional but not sad, showing longing and love. About 3-4 sentences.{anniversary_context}",
                
                'good_morning': f"Write a warm good morning message from {sender_name} to {receiver_name} to start their day with love and positivity. Use morning emojis like ☀️ 🌅 ☕ 🌸. About 2-3 sentences.{anniversary_context}",
                
                'good_night': f"Write a sweet good night message from {sender_name} to {receiver_name} to help them sleep with love and peace. Use night emojis like 🌙 ✨ 😴 💤. About 2-3 sentences.{anniversary_context}",
                
                'appreciation': f"Write an appreciation message from {sender_name} to {receiver_name} thanking them for being in their life. Use grateful emojis like 🙏 💝 🌹 ✨. Heartfelt and genuine, highlighting specific qualities. About 3-4 sentences.{anniversary_context}",
                
                'anniversary': f"Write a beautiful anniversary message from {sender_name} to {receiver_name} celebrating their love and journey together. Include reference to their anniversary. Use celebration emojis like 🎉 🥂 💑 🎊. Special and romantic. About 4-5 sentences.{anniversary_context}",
                
                'sorry': f"Write a sincere apology message from {sender_name} to {receiver_name}. Use sincere emojis like 😔 💔 🫂 🙏. Make it heartfelt and genuine, showing remorse, understanding, and love. About 3-4 sentences.{anniversary_context}",
                
                'general': f"Write a loving message from {sender_name} to {receiver_name} about your relationship. Make it warm, caring, and positive. Use appropriate emojis. About 3-4 sentences.{anniversary_context}"
            }
            
            prompt = prompts.get(message_type, prompts['general'])
        
        print(f"🎨 Generating {message_type} message for {sender_name} -> {receiver_name}")
        print(f"📝 Prompt: {prompt[:200]}...")
        
        # Get the model manager
        model_manager = get_huggingface_model(key_manager)
        if not model_manager:
            print(f"❌ Model manager not available")
            return jsonify({
                'success': False,
                'error': 'model_unavailable',
                'message': 'AI model is temporarily unavailable. Please try again.',
                'offline_mode': True
            }), 503
        
        # Try to generate message with retry logic
        max_retries = 2
        generated_text = None
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 Generation attempt {attempt + 1}/{max_retries}")
                
                # Generate message
                generated_text = model_manager.query_model(prompt, max_length=200, message_type=message_type)
                
                if generated_text:
                    print(f"✅ Generated text: {generated_text[:100]}...")
                    
                    # Clean up the generated text
                    if prompt in generated_text:
                        generated_text = generated_text.replace(prompt, '').strip()
                    
                    # Remove any remaining prompt artifacts
                    if sender_name in generated_text and 'Write a' in generated_text[:50]:
                        parts = generated_text.split(sender_name, 1)
                        if len(parts) > 1:
                            generated_text = sender_name + parts[1]
                    
                    # Ensure the message has emojis (fallback in case model didn't add any)
                    has_emoji = any(char in generated_text for char in ['❤', '💕', '😂', '😊', '🌙', '☀️', '🎉', '🙏', '😔', '🥺', '✨', '💖', '🌹'])
                    
                    # Message type to emoji mapping for fallback
                    emoji_map = {
                        'romantic': ['❤️', '💕', '💖', '🌹'],
                        'funny': ['😂', '😆', '🎉', '🤪'],
                        'missing': ['🥺', '💫', '🌙', '💭'],
                        'good_morning': ['☀️', '🌅', '☕', '🌸'],
                        'good_night': ['🌙', '✨', '😴', '💤'],
                        'appreciation': ['🙏', '💝', '🌹', '✨'],
                        'anniversary': ['🎉', '🥂', '💑', '🎊'],
                        'sorry': ['😔', '💔', '🫂', '🙏'],
                        'custom': ['💭', '✨', '💫', '🌟'],
                        'general': ['💖', '✨', '💫', '🌟']
                    }
                    
                    if not has_emoji and message_type in emoji_map:
                        import random
                        emojis = emoji_map[message_type]
                        selected_emojis = ' '.join(random.sample(emojis, min(2, len(emojis))))
                        generated_text = f"{selected_emojis} {generated_text} {selected_emojis}"
                        print(f"🎨 Added emojis to message")
                    
                    # Update session title if this is the first message
                    message_count = ChatHistory.query.filter_by(session_id=chat_session.id).count()
                    if message_count == 0:
                        # Set title based on first message
                        preview = generated_text[:50] + '...' if len(generated_text) > 50 else generated_text
                        chat_session.title = f"{message_type.replace('_', ' ').title()}: {preview}"
                        db.session.commit()
                        print(f"📝 Updated session title to: {chat_session.title}")
                    
                    # Save to chat history with session_id and sender_type
                    # IMPORTANT: message_type is the AI message type (romantic, funny, etc.) NOT 'chat'
                    chat = ChatHistory(
                        session_id=chat_session.id,
                        couple_id=user_id,
                        sender_name=sender_name,
                        sender_type=user_type,
                        receiver_name=receiver_name,
                        message_type=message_type,  # This is 'romantic', 'funny', etc. NOT 'chat'
                        message=generated_text
                    )
                    db.session.add(chat)
                    
                    # Update session updated_at
                    chat_session.updated_at = datetime.utcnow()
                    
                    db.session.commit()
                    
                    print(f"✅ AI message saved with ID: {chat.id}, type: {message_type}")
                    
                    # Create notification for partner (optional)
                    global notification_manager
                    if notification_manager:
                        try:
                            partner_type = 'girl' if user_type == 'boy' else 'boy'
                            notification_manager.create_notification(
                                user_id=user_id,
                                user_type=partner_type,
                                title=f'New {message_type.title()} Message 💌',
                                message=f'{sender_name} shared a {message_type} message with you',
                                icon='fa-heart',
                                color='primary'
                            )
                        except Exception as e:
                            print(f"⚠️ Notification error: {str(e)}")
                    
                    break
                
            except Exception as e:
                print(f"❌ Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)  # Wait 2 seconds before retry
        
        if generated_text:
            return jsonify({
                'success': True,
                'message': generated_text,
                'type': message_type,
                'chat_id': chat.id,
                'session_id': chat_session.id,
                'session_uuid': chat_session.session_uuid,
                'sender_type': user_type,
                'sender_name': sender_name,
                'receiver_name': receiver_name,
                'timestamp': chat.created_at.isoformat(),
                'formatted_time': chat.created_at.strftime('%I:%M %p')
            })
        else:
            print(f"❌ Failed to generate message after {max_retries} attempts")
            return jsonify({
                'success': False,
                'error': 'generation_failed',
                'message': 'Failed to generate message. Please try again.',
                'offline_mode': True
            }), 500
        
    except Exception as e:
        print(f"❌ Message generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An unexpected error occurred while generating message.',
            'offline_mode': True
        }), 500

@app.route('/api/key-stats')
def key_stats():
    """Endpoint to check key status"""
    global key_manager
    
    if not key_manager:
        return jsonify({
            'success': False,
            'error': 'Key manager not initialized',
            'debug_info': {
                'api_key_configured': bool(app.config.get('HUGGINGFACE_API_KEY')),
                'api_key_preview': app.config.get('HUGGINGFACE_API_KEY', '')[:10] + '...' if app.config.get('HUGGINGFACE_API_KEY') else None,
                'key_manager_object': str(key_manager)
            }
        }), 500
    
    try:
        stats = key_manager.get_stats()
        return jsonify({
            'success': True,
            'stats': stats,
            'model': app.config.get('HUGGINGFACE_MODEL'),
            'debug_info': {
                'api_key_configured': bool(app.config.get('HUGGINGFACE_API_KEY')),
                'api_key_preview': app.config.get('HUGGINGFACE_API_KEY', '')[:10] + '...' if app.config.get('HUGGINGFACE_API_KEY') else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_info': {
                'api_key_configured': bool(app.config.get('HUGGINGFACE_API_KEY'))
            }
        }), 500

@app.route('/api/get-partner-phone')
def get_partner_phone():
    """Get partner's phone number for WhatsApp sharing"""
    try:
        # Get user_id from session
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id or not user_type:
            return jsonify({
                'success': False,
                'error': 'not_logged_in',
                'message': 'Please login first'
            }), 401
        
        # Fetch couple from database
        couple = db.session.get(Couple, user_id)
        if not couple:
            session.clear()
            return jsonify({
                'success': False,
                'error': 'session_expired',
                'message': 'Session expired. Please login again.'
            }), 401
        
        # Return the partner's phone number based on user type
        if user_type == 'boy':
            return jsonify({
                'success': True,
                'phone': couple.girl_mobile
            })
        else:
            return jsonify({
                'success': True,
                'phone': couple.boy_mobile
            })
            
    except Exception as e:
        print(f"Error getting partner phone: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/api/check-session')
def check_session():
    """Check if user session is valid"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if user_id and user_type:
        couple = db.session.get(Couple, user_id)
        if couple:
            return jsonify({
                'success': True,
                'logged_in': True,
                'user_type': user_type
            })
    
    return jsonify({
        'success': True,
        'logged_in': False
    })

@app.route('/api/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': 'not_found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 'server_error',
        'message': 'An internal server error occurred'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting ForeverUs server on port {port}...")
    print(f"📱 Access the application at http://127.0.0.1:{port}")
    print(f"👨‍💼 Admin panel at http://127.0.0.1:{port}/admin")
    app.run(debug=True, host='0.0.0.0', port=port)