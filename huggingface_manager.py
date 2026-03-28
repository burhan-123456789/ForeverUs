import requests
import time
import random
from typing import Optional, Dict, Any, List
from datetime import datetime

class HuggingFaceManager:
    def __init__(self, api_keys: List[str], model_name: str = 'Qwen/Qwen2.5-72B-Instruct'):
        """
        Initialize with Hugging Face's Inference Providers API using only Qwen model
        """
        self.api_key = api_keys[0] if api_keys else None
        self.model_name = model_name  # Will always use Qwen/Qwen2.5-72B-Instruct
        self.api_url = "https://router.huggingface.co/v1/chat/completions"
        self.last_used = 0
        self.error_count = 0
        self.success_count = 0
        self.cooldown_until = 0
        self.total_uses = 0
        self.consecutive_failures = 0
        
        # Common romantic emojis for fallback
        self.romantic_emojis = ['❤️', '💕', '💖', '💗', '💓', '💘', '💝', '💞', '🥰', '😘', '💋', '🌹', '🌸', '✨', '⭐', '💫', '💑', '👩‍❤️‍👨', '💏', '💌']
        
        print(f"✅ HuggingFaceManager initialized with router API")
        print(f"📡 Using endpoint: {self.api_url}")
        print(f"🤖 Using model: {self.model_name} (Qwen 2.5 72B)")
        print(f"✨ This model is confirmed working")
        print(f"😊 Emoji support enabled")
    
    def is_available(self) -> bool:
        """Check if the key is available for use"""
        current_time = time.time()
        return current_time >= self.cooldown_until
    
    def _add_emojis_to_message(self, message: str, message_type: str) -> str:
        """Add relevant emojis to the message based on type"""
        
        # Message type to emoji mapping
        emoji_map = {
            'romantic': ['❤️', '💕', '💖', '💗', '💓', '🥰', '💘', '💞'],
            'funny': ['😂', '😆', '🤣', '😄', '😁', '😜', '😝', '🎉'],
            'missing': ['🥺', '💔', '😢', '😔', '💫', '⭐', '🌙', '💭'],
            'good_morning': ['☀️', '🌅', '🌞', '🌤️', '🌈', '🌸', '🌺', '☕'],
            'good_night': ['🌙', '✨', '💫', '⭐', '🌜', '😴', '💤', '🌠'],
            'appreciation': ['🙏', '💝', '💖', '🌹', '🌸', '✨', '🎁', '🏆'],
            'anniversary': ['🎉', '🥂', '💍', '💑', '👰', '🤵', '🎊', '🎈'],
            'sorry': ['😔', '💔', '🫂', '😞', '💝', '🌹', '🕊️', '🤗'],
            'general': ['💭', '✨', '💫', '🤔', '💡', '🌟']
        }
        
        # Get emojis for this message type (default to romantic if type not found)
        emojis = emoji_map.get(message_type, self.romantic_emojis)
        
        # Select 1-3 random emojis
        num_emojis = random.randint(1, 3)
        selected_emojis = random.sample(emojis, min(num_emojis, len(emojis)))
        emoji_string = ' '.join(selected_emojis)
        
        # Add emojis to beginning and end
        return f"{emoji_string} {message} {emoji_string}"
    
    def query_model(self, prompt: str, max_length: int = 150, message_type: str = 'romantic') -> Optional[str]:
        """
        Query Hugging Face using the Qwen model only
        """
        if not self.is_available():
            wait_time = int(self.cooldown_until - time.time())
            print(f"⏳ Key on cooldown. Wait {wait_time} seconds")
            return None
        
        if not self.api_key:
            print("❌ No API key configured")
            return None
        
        # Use only the Qwen model (no fallbacks needed since it's working)
        return self._try_model(self.model_name, prompt, max_length, message_type)
    
    def _try_model(self, model: str, prompt: str, max_length: int, message_type: str) -> Optional[str]:
        """Query the Qwen model"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Enhanced system prompt to encourage emoji usage
        system_prompts = {
            'romantic': "You are a romantic partner. Write short, sweet, loving messages. Use appropriate emojis like ❤️ 💕 💖 in your response. Keep it to 2-3 sentences.",
            'funny': "You are a playful partner. Write funny, light-hearted messages that will make them laugh. Use fun emojis like 😂 😆 🎉. Keep it to 2-3 sentences.",
            'missing': "You are a loving partner who misses their significant other. Write emotional but sweet messages. Use emojis like 🥺 💫 🌙. Keep it to 2-3 sentences.",
            'good_morning': "You are a cheerful partner. Write a warm good morning message. Use morning emojis like ☀️ 🌅 ☕. Keep it to 2-3 sentences.",
            'good_night': "You are a caring partner. Write a sweet good night message. Use night emojis like 🌙 ✨ 😴. Keep it to 2-3 sentences.",
            'appreciation': "You are a grateful partner. Write an appreciation message. Use grateful emojis like 🙏 💝 🌹. Keep it to 2-3 sentences.",
            'anniversary': "You are celebrating an anniversary. Write a special romantic message. Use celebration emojis like 🎉 🥂 💑. Keep it to 3-4 sentences.",
            'sorry': "You are apologizing sincerely. Write a heartfelt sorry message. Use sincere emojis like 😔 💔 🫂. Keep it to 2-3 sentences.",
            'general': "You are a helpful and caring AI assistant. Provide thoughtful, kind responses. Use appropriate emojis to make your responses warm and friendly."
        }
        
        # Get the appropriate system prompt or use default with emojis
        system_prompt = system_prompts.get(message_type, 
            "You are a romantic partner. Write sweet messages with appropriate emojis. Keep it to 2-3 sentences.")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_length,
            "temperature": 0.8,  # Slightly higher for more creative romantic messages
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            print(f"📡 Querying Qwen model for {message_type} message...")
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully generated message")
                
                self.consecutive_failures = 0
                self.cooldown_until = time.time() + 1  # Short cooldown
                self.success_count += 1
                self.total_uses += 1
                self.last_used = time.time()
                
                # Extract the generated text
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {})
                    content = message.get('content', '')
                    
                    # Clean up the response
                    content = content.strip()
                    
                    # Remove any system prompt artifacts if they appear
                    if "You are a" in content:
                        # Find the actual message after the system prompt
                        lines = content.split('\n')
                        for line in lines:
                            if line and "You are a" not in line and "Write" not in line:
                                content = line
                                break
                    
                    # Check if the message already has emojis
                    has_emoji = any(char in content for char in ['❤', '💕', '😂', '😊', '🌙', '☀️', '🎉', '🙏'])
                    
                    # If no emojis found, add them
                    if not has_emoji:
                        content = self._add_emojis_to_message(content, message_type)
                    
                    return content
                
                return str(result)
                
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                self.cooldown_until = time.time() + retry_after
                print(f"⏳ Rate limited. Cool down for {retry_after}s")
                self.error_count += 1
                return None
                
            elif response.status_code == 503:
                print(f"⏳ Model loading...")
                time.sleep(2)
                return None
                
            else:
                print(f"❌ HTTP Error {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                self.error_count += 1
                self.consecutive_failures += 1
                self.cooldown_until = time.time() + 5
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout error")
            self.error_count += 1
            self.cooldown_until = time.time() + 5
            return None
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.error_count += 1
            self.cooldown_until = time.time() + 5
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        current_time = time.time()
        is_available = self.is_available()
        cooldown_remaining = max(0, int(self.cooldown_until - current_time)) if not is_available else 0
        
        return {
            'total_uses': self.total_uses,
            'successful_uses': self.success_count,
            'failed_uses': self.error_count,
            'success_rate': f"{(self.success_count / max(1, self.total_uses) * 100):.1f}%",
            'available': is_available,
            'cooldown_remaining': cooldown_remaining,
            'model': self.model_name,
            'model_info': 'Qwen/Qwen2.5-72B-Instruct (with emoji support)',
            'emoji_enabled': True,
            'timestamp': datetime.now().isoformat()
        }

# Singleton instance
key_manager = None

def init_huggingface_manager(api_keys: list, model_name: str = 'Qwen/Qwen2.5-72B-Instruct'):
    """
    Initialize with the working Qwen model
    """
    global key_manager
    if api_keys and len(api_keys) > 0:
        print(f"🔄 Initializing Hugging Face with Qwen model...")
        key_manager = HuggingFaceManager(api_keys, model_name)
    else:
        key_manager = None
    return key_manager

def get_huggingface_model(manager=None):
    """Get the configured model instance"""
    global key_manager
    mgr = manager if manager is not None else key_manager
    
    if not mgr:
        print("❌ HuggingFaceManager not initialized")
        return None
    
    if not mgr.is_available():
        print("⚠️ Key is on cooldown")
        return None
    
    return mgr