import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///foreverus.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Hugging Face API key
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
    
    # Use ONLY the Qwen model which is confirmed working
    HUGGINGFACE_MODEL = 'Qwen/Qwen2.5-72B-Instruct'
    
    # Keep for backward compatibility
    HUGGINGFACE_API_KEYS = [HUGGINGFACE_API_KEY] if HUGGINGFACE_API_KEY else []
    
    # Flask-Admin configuration
    FLASK_ADMIN_SWATCH = 'cerulean'
    
    # Admin credentials (change in production)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'foreverus123')
    
    # Notification settings
    NOTIFICATION_POLLING_INTERVAL = 5  # seconds
    MAX_NOTIFICATIONS_PER_USER = 100