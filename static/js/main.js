// PWA Installation
let deferredPrompt;
const installPrompt = document.getElementById('install-prompt');
const installButton = document.getElementById('install-app');
const maybeLaterButton = document.getElementById('maybe-later');

// Check if app is already installed
if (window.matchMedia('(display-mode: standalone)').matches) {
    // App is installed, hide install prompt
    if (installPrompt) {
        installPrompt.style.display = 'none';
    }
} else {
    // Show install prompt after 3 seconds if not dismissed
    setTimeout(() => {
        if (installPrompt && !localStorage.getItem('installPromptDismissed')) {
            installPrompt.style.display = 'block';
        }
    }, 3000);
}

// Listen for beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // Show install prompt if not dismissed
    if (!localStorage.getItem('installPromptDismissed')) {
        installPrompt.style.display = 'block';
    }
});

// Handle install button click
if (installButton) {
    installButton.addEventListener('click', async () => {
        if (!deferredPrompt) {
            return;
        }
        
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('User accepted the install prompt');
            // Track installation
            localStorage.setItem('appInstalled', 'true');
        }
        
        deferredPrompt = null;
        installPrompt.style.display = 'none';
    });
}

// Handle maybe later button
if (maybeLaterButton) {
    maybeLaterButton.addEventListener('click', () => {
        installPrompt.style.display = 'none';
        localStorage.setItem('installPromptDismissed', 'true');
        
        // Show a small reminder after 7 days
        setTimeout(() => {
            localStorage.removeItem('installPromptDismissed');
        }, 7 * 24 * 60 * 60 * 1000);
    });
}

// Login Form Handler
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(loginForm);
        const data = {
            unique_id: formData.get('unique_id'),
            user_type: formData.get('user_type')
        };
        
        // Show loading state
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Show welcome animation
                showWelcomeAnimation();
                
                // Redirect to dashboard after animation
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 2000);
            } else {
                // Show error message
                showNotification(result.message || 'Invalid ID. Please try again.', 'error');
                
                // Reset button
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Login error:', error);
            showNotification('Connection error. Please check your internet.', 'error');
            
            // Reset button
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
        }
    });
}

// Registration Form Handler
const registerForm = document.getElementById('register-form');
if (registerForm) {
    // Set min date for anniversary (today)
    const today = new Date().toISOString().split('T')[0];
    const anniversaryInput = document.getElementById('anniversary-date');
    if (anniversaryInput) {
        anniversaryInput.setAttribute('max', today);
    }
    
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate form
        if (!validateRegistrationForm()) {
            return;
        }
        
        const formData = new FormData(registerForm);
        const data = {
            boy_name: formData.get('boy_name'),
            girl_name: formData.get('girl_name'),
            boy_mobile: formData.get('boy_mobile'),
            girl_mobile: formData.get('girl_mobile'),
            boy_age: formData.get('boy_age'),
            girl_age: formData.get('girl_age'),
            anniversary_date: formData.get('anniversary_date')
        };
        
        // Show loading state
        const submitBtn = document.getElementById('register-btn');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating your space...';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Show success modal with IDs
                document.getElementById('boy-id').textContent = result.boy_id;
                document.getElementById('girl-id').textContent = result.girl_id;
                document.getElementById('success-modal').style.display = 'flex';
                
                // Reset form
                registerForm.reset();
            } else {
                showNotification(result.message || 'Registration failed. Please try again.', 'error');
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Registration error:', error);
            showNotification('Connection error. Please check your internet.', 'error');
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
        }
    });
}

// Form validation function
function validateRegistrationForm() {
    const boyMobile = document.getElementById('boy-mobile').value;
    const girlMobile = document.getElementById('girl-mobile').value;
    const boyAge = parseInt(document.getElementById('boy-age').value);
    const girlAge = parseInt(document.getElementById('girl-age').value);
    
    // Validate mobile numbers (10 digits)
    const mobileRegex = /^\d{10}$/;
    if (!mobileRegex.test(boyMobile)) {
        showNotification('Boy\'s mobile number must be 10 digits', 'error');
        return false;
    }
    if (!mobileRegex.test(girlMobile)) {
        showNotification('Girl\'s mobile number must be 10 digits', 'error');
        return false;
    }
    
    // Validate ages (minimum 18)
    if (boyAge < 18 || boyAge > 120) {
        showNotification('Boy\'s age must be between 18 and 120', 'error');
        return false;
    }
    if (girlAge < 18 || girlAge > 120) {
        showNotification('Girl\'s age must be between 18 and 120', 'error');
        return false;
    }
    
    return true;
}

// Welcome Animation
function showWelcomeAnimation() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML = `
        <div class="loading-content">
            <i class="fas fa-heart beating-heart"></i>
            <h2>Welcome Back! ❤️</h2>
            <p>Entering your private love universe...</p>
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    setTimeout(() => {
        overlay.remove();
    }, 2000);
}

// Show notification function
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Show notification with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Copy Message
const copyBtn = document.getElementById('copy-message');
if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
        const messageElement = document.getElementById('ai-response');
        const message = messageElement.innerText || messageElement.textContent;
        
        if (!message || message === 'Click generate to create a romantic message...') {
            showNotification('Please generate a message first!', 'error');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(message);
            
            // Show success state
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            copyBtn.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
            
            setTimeout(() => {
                copyBtn.innerHTML = originalHTML;
                copyBtn.style.background = '';
            }, 2000);
            
            showNotification('Message copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy message', 'error');
        }
    });
}

// Share on WhatsApp
const shareBtn = document.getElementById('share-whatsapp');
if (shareBtn) {
    shareBtn.addEventListener('click', async () => {
        const messageElement = document.getElementById('ai-response');
        const message = messageElement.innerText || messageElement.textContent;
        
        if (!message || message === 'Click generate to create a romantic message...') {
            showNotification('Please generate a message first!', 'error');
            return;
        }
        
        // Show loading state
        const originalHTML = shareBtn.innerHTML;
        shareBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        shareBtn.disabled = true;
        
        try {
            const response = await fetch('/api/get-partner-phone');
            const result = await response.json();
            
            if (result.success) {
                const phone = result.phone.replace(/\D/g, '');
                const encodedMessage = encodeURIComponent(message + '\n\n- Sent with ❤️ from ForeverUs');
                const whatsappUrl = `https://wa.me/${phone}?text=${encodedMessage}`;
                
                window.open(whatsappUrl, '_blank');
            } else {
                showNotification('Could not get partner\'s phone number', 'error');
            }
        } catch (error) {
            console.error('WhatsApp share error:', error);
            showNotification('Failed to share on WhatsApp', 'error');
        } finally {
            // Reset button
            shareBtn.innerHTML = originalHTML;
            shareBtn.disabled = false;
        }
    });
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    const modal = document.getElementById('success-modal');
    if (e.target === modal) {
        modal.style.display = 'none';
    }
});

// Add keyboard support for modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('success-modal');
        if (modal && modal.style.display === 'flex') {
            modal.style.display = 'none';
        }
    }
});

// Check session on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Skip session check on login and register pages
    const isLoginPage = window.location.pathname === '/';
    const isRegisterPage = window.location.pathname === '/register';
    
    if (!isLoginPage && !isRegisterPage) {
        try {
            const response = await fetch('/api/check-session');
            const data = await response.json();
            
            if (!data.logged_in) {
                // Redirect to login if not logged in
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Session check error:', error);
        }
    }
});

// Add smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading dots animation styles
const style = document.createElement('style');
style.textContent = `
    .loading-dots {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    
    .loading-dots span {
        width: 10px;
        height: 10px;
        margin: 0 5px;
        background: #ff4d6d;
        border-radius: 50%;
        animation: dots 1.4s infinite ease-in-out;
    }
    
    .loading-dots span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .loading-dots span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes dots {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: white;
        border-radius: 50px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 10px;
        transform: translateX(120%);
        transition: transform 0.3s ease;
        z-index: 9999;
    }
    
    .notification.show {
        transform: translateX(0);
    }
    
    .notification.error {
        background: #ff4757;
        color: white;
    }
    
    .notification.success {
        background: #28a745;
        color: white;
    }
    
    .notification.info {
        background: #17a2b8;
        color: white;
    }
`;

document.head.appendChild(style);