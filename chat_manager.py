from huggingface_manager import get_huggingface_model
import random
import time
from datetime import datetime

class ChatManager:
    """Manager for AI chat functionality"""
    
    def __init__(self, key_manager):
        self.key_manager = key_manager
        self.model_manager = get_huggingface_model(key_manager)
        
        # Conversation starters and responses
        self.conversation_starters = [
            "How was your day today?",
            "What's something that made you smile today?",
            "Tell me something you love about your partner.",
            "What's your favorite memory together?",
            "If you could go anywhere in the world with your partner, where would it be?",
            "What's a small thing your partner does that you appreciate?",
            "Describe your perfect date night.",
            "What's a dream you have for your future together?",
            "What's something new you'd like to try with your partner?",
            "What quality do you admire most in your partner?"
        ]
        
        self.follow_up_prompts = [
            "That's beautiful! Tell me more about that.",
            "How did that make you feel?",
            "What do you think your partner would say about that?",
            "When was the last time that happened?",
            "What would make that moment even more special?",
            "How can you create more moments like that?",
            "What did you learn from that experience?",
            "How has that strengthened your relationship?"
        ]
    
    def generate_response(self, user_message, sender_name, user_type, message_type='general'):
        """Generate AI response to user message"""
        if not self.model_manager:
            return self._get_fallback_response(user_message)
        
        try:
            # Create prompt for AI
            prompt = f"User {sender_name} says: '{user_message}'. Respond as a caring relationship coach and friend. Be supportive, empathetic, and helpful. Keep it to 2-3 sentences."
            
            # Try to get AI response
            response = self.model_manager.query_model(prompt, max_length=150, message_type=message_type)
            
            if response:
                return response
            else:
                return self._get_fallback_response(user_message)
                
        except Exception as e:
            print(f"Error generating chat response: {str(e)}")
            return self._get_fallback_response(user_message)
    
    def _get_fallback_response(self, user_message):
        """Get fallback response when AI is unavailable"""
        fallbacks = [
            "That's really sweet! 💕 Tell me more about how you feel.",
            "I love hearing that! 😊 What's on your mind today?",
            "That's wonderful! 🌟 How can I help you express that to your partner?",
            "I appreciate you sharing that with me. 💝 How are you feeling right now?",
            "Thank you for opening up! 🫂 What would make this moment even better?",
            "That's beautiful! ✨ Would you like some ideas on how to surprise your partner?",
            "I'm here for you! 💫 What would you like to talk about next?",
            "Your relationship sounds amazing! 💑 What's something new you'd like to try together?"
        ]
        
        # Check if message contains certain keywords for more relevant responses
        user_message_lower = user_message.lower()
        
        if any(word in user_message_lower for word in ['love', '❤️', 'heart', 'sweet']):
            return "Love is beautiful! 💖 Would you like to express this feeling to your partner with a special message?"
        elif any(word in user_message_lower for word in ['miss', 'away', 'far']):
            return "Distance can be hard, but it makes the heart grow fonder! 🥺 Would you like to send a 'miss you' message?"
        elif any(word in user_message_lower for word in ['sorry', 'apologize', 'regret']):
            return "It takes courage to apologize. 💔 Would you like help crafting a sincere apology message?"
        elif any(word in user_message_lower for word in ['thank', 'grateful', 'appreciate']):
            return "Gratitude strengthens relationships! 🙏 Would you like to write an appreciation message?"
        elif any(word in user_message_lower for word in ['anniversary', 'celebrate']):
            return "Anniversaries are special milestones! 🎉 Would you like a beautiful anniversary message?"
        else:
            return random.choice(fallbacks)
    
    def get_conversation_starter(self):
        """Get a random conversation starter"""
        return random.choice(self.conversation_starters)
    
    def get_follow_up(self):
        """Get a random follow-up question"""
        return random.choice(self.follow_up_prompts)