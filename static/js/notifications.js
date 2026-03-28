// Notification system using HTTP polling
class NotificationManager {
    constructor() {
        this.pollingInterval = 5000; // 5 seconds
        this.isPolling = false;
        this.notifications = [];
        this.unreadCount = 0;
        this.notificationBell = document.getElementById('notification-bell');
        this.notificationBadge = document.getElementById('notification-badge');
        this.notificationDropdown = document.getElementById('notification-dropdown');
        this.notificationList = document.getElementById('notification-list');
        this.markAllReadBtn = document.getElementById('mark-all-read');
        this.clearAllBtn = document.getElementById('clear-all-notifications');
        
        this.init();
    }
    
    init() {
        // Start polling if user is logged in
        this.checkLoginStatus();
        
        // Add event listeners
        if (this.notificationBell) {
            this.notificationBell.addEventListener('click', () => this.toggleDropdown());
        }
        
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', () => this.markAllAsRead());
        }
        
        if (this.clearAllBtn) {
            this.clearAllBtn.addEventListener('click', () => this.clearAll());
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (this.notificationDropdown && 
                !this.notificationBell.contains(e.target) && 
                !this.notificationDropdown.contains(e.target)) {
                this.notificationDropdown.classList.remove('show');
            }
        });
    }
    
    async checkLoginStatus() {
        try {
            const response = await fetch('/api/check-session');
            const data = await response.json();
            
            if (data.logged_in) {
                this.startPolling();
            }
        } catch (error) {
            console.error('Error checking login status:', error);
        }
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.poll();
    }
    
    stopPolling() {
        this.isPolling = false;
    }
    
    async poll() {
        if (!this.isPolling) return;
        
        try {
            await this.fetchNotifications();
        } catch (error) {
            console.error('Polling error:', error);
        }
        
        // Schedule next poll
        setTimeout(() => this.poll(), this.pollingInterval);
    }
    
    async fetchNotifications() {
        try {
            const response = await fetch('/api/notifications');
            const data = await response.json();
            
            if (data.success) {
                this.notifications = data.notifications;
                this.unreadCount = data.unread_count;
                this.updateUI();
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }
    
    updateUI() {
        // Update badge
        if (this.notificationBadge) {
            this.notificationBadge.textContent = this.unreadCount;
            this.notificationBadge.style.display = this.unreadCount > 0 ? 'flex' : 'none';
        }
        
        // Update bell icon pulse
        if (this.notificationBell) {
            if (this.unreadCount > 0) {
                this.notificationBell.classList.add('has-notifications');
            } else {
                this.notificationBell.classList.remove('has-notifications');
            }
        }
        
        // Update notification list
        this.renderNotifications();
    }
    
    renderNotifications() {
        if (!this.notificationList) return;
        
        if (this.notifications.length === 0) {
            this.notificationList.innerHTML = `
                <div class="notification-empty">
                    <i class="fas fa-bell"></i>
                    <p>No notifications</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        this.notifications.forEach(notif => {
            const notifClass = notif.is_read ? 'notification-item' : 'notification-item unread';
            const timeAgo = this.getTimeAgo(new Date(notif.created_at));
            
            html += `
                <div class="${notifClass}" data-id="${notif.id}">
                    <div class="notification-icon ${notif.color}">
                        <i class="fas ${notif.icon}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">${notif.title}</div>
                        <div class="notification-message">${notif.message}</div>
                        <div class="notification-time">${timeAgo}</div>
                    </div>
                    ${!notif.is_read ? '<div class="notification-dot"></div>' : ''}
                </div>
            `;
        });
        
        this.notificationList.innerHTML = html;
        
        // Add click event to mark as read
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const id = item.dataset.id;
                if (id) {
                    this.markAsRead([id]);
                }
            });
        });
    }
    
    async markAsRead(notificationIds) {
        try {
            const response = await fetch('/api/notifications/read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ notification_ids: notificationIds })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update local state
                this.notifications = this.notifications.map(n => {
                    if (notificationIds.includes(n.id.toString())) {
                        return { ...n, is_read: true };
                    }
                    return n;
                });
                
                this.unreadCount = this.notifications.filter(n => !n.is_read).length;
                this.updateUI();
            }
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update local state
                this.notifications = this.notifications.map(n => ({ ...n, is_read: true }));
                this.unreadCount = 0;
                this.updateUI();
                
                this.showToast('All notifications marked as read', 'success');
            }
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    }
    
    async clearAll() {
        if (!confirm('Clear all notifications?')) return;
        
        try {
            const response = await fetch('/api/notifications/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.notifications = [];
                this.unreadCount = 0;
                this.updateUI();
                
                this.showToast('All notifications cleared', 'success');
            }
        } catch (error) {
            console.error('Error clearing notifications:', error);
        }
    }
    
    toggleDropdown() {
        if (this.notificationDropdown) {
            this.notificationDropdown.classList.toggle('show');
            
            // Mark all as read when opening dropdown
            if (this.notificationDropdown.classList.contains('show') && this.unreadCount > 0) {
                this.markAllAsRead();
            }
        }
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        if (diffSec < 60) {
            return 'Just now';
        } else if (diffMin < 60) {
            return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
        } else if (diffHour < 24) {
            return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
        } else if (diffDay < 7) {
            return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `notification ${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 'fa-check-circle'}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// Add notification styles
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    /* Notification Bell Container */
    .notification-bell-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1002;
    }
    
    .notification-bell {
        width: 50px;
        height: 50px;
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
        border-radius: 50%;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        transition: all 0.3s ease;
        position: relative;
        box-shadow: var(--shadow);
    }
    
    .notification-bell:hover {
        background: var(--primary);
        transform: scale(1.1);
    }
    
    .notification-bell.has-notifications {
        animation: bellShake 0.5s ease infinite;
    }
    
    .notification-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: linear-gradient(135deg, var(--primary), var(--gradient-end));
        color: white;
        font-size: 0.7rem;
        min-width: 20px;
        height: 20px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 5px;
        border: 2px solid var(--glass-bg);
        font-weight: 600;
    }
    
    /* Notification Dropdown */
    .notification-dropdown {
        position: absolute;
        top: 60px;
        right: 0;
        width: 350px;
        max-width: calc(100vw - 40px);
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 15px;
        box-shadow: var(--shadow);
        display: none;
        z-index: 1003;
        overflow: hidden;
    }
    
    .notification-dropdown.show {
        display: block;
        animation: slideDown 0.3s ease;
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .notification-header {
        padding: 15px 20px;
        border-bottom: 1px solid var(--glass-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .notification-header h3 {
        font-size: 1.1rem;
        color: var(--text-primary);
        margin: 0;
    }
    
    .mark-read-btn {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid var(--glass-border);
        border-radius: 8px;
        color: var(--text-primary);
        width: 35px;
        height: 35px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .mark-read-btn:hover {
        background: var(--primary);
        transform: scale(1.1);
    }
    
    .notification-list {
        max-height: 400px;
        overflow-y: auto;
        padding: 10px;
    }
    
    .notification-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        margin: 5px 0;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid var(--glass-border);
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .notification-item:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateX(5px);
    }
    
    .notification-item.unread {
        background: rgba(255, 77, 109, 0.1);
        border-color: var(--primary);
    }
    
    .notification-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .notification-icon.primary {
        background: rgba(255, 77, 109, 0.2);
        color: #ff4d6d;
    }
    
    .notification-icon.success {
        background: rgba(0, 184, 148, 0.2);
        color: #00b894;
    }
    
    .notification-icon.info {
        background: rgba(23, 162, 184, 0.2);
        color: #17a2b8;
    }
    
    .notification-icon.warning {
        background: rgba(255, 193, 7, 0.2);
        color: #ffc107;
    }
    
    .notification-content {
        flex: 1;
        min-width: 0;
    }
    
    .notification-title {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 3px;
        font-size: 0.95rem;
    }
    
    .notification-message {
        color: var(--text-secondary);
        font-size: 0.85rem;
        margin-bottom: 5px;
        line-height: 1.4;
        word-wrap: break-word;
    }
    
    .notification-time {
        font-size: 0.7rem;
        color: var(--text-secondary);
        opacity: 0.7;
    }
    
    .notification-dot {
        width: 8px;
        height: 8px;
        background: var(--primary);
        border-radius: 50%;
        position: absolute;
        top: 10px;
        right: 10px;
    }
    
    .notification-empty {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-secondary);
    }
    
    .notification-empty i {
        font-size: 50px;
        color: var(--primary);
        margin-bottom: 15px;
        opacity: 0.5;
    }
    
    .notification-footer {
        padding: 15px 20px;
        border-top: 1px solid var(--glass-border);
        text-align: center;
    }
    
    .clear-all-btn {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid var(--glass-border);
        border-radius: 8px;
        color: var(--text-primary);
        padding: 8px 15px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    
    .clear-all-btn:hover {
        background: #ff4757;
        transform: translateY(-2px);
    }
    
    /* Loading state */
    .notification-loading {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-secondary);
    }
    
    .notification-loading i {
        font-size: 30px;
        margin-bottom: 10px;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    @keyframes bellShake {
        0%, 100% { transform: rotate(0); }
        25% { transform: rotate(15deg); }
        75% { transform: rotate(-15deg); }
    }
    
    /* Mobile Responsive */
    @media (max-width: 768px) {
        .notification-bell-container {
            top: 15px;
            right: 15px;
        }
        
        .notification-bell {
            width: 45px;
            height: 45px;
            font-size: 1rem;
        }
        
        .notification-dropdown {
            position: fixed;
            top: 70px;
            right: 10px;
            left: 10px;
            width: auto;
            max-width: none;
        }
    }
`;

document.head.appendChild(notificationStyles);