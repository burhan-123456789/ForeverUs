// Real-time Couple Chat functionality with HTTP polling

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-message');
    const messagesContainer = document.getElementById('chat-messages');
    const loadingOverlay = document.getElementById('loading-overlay');
    const refreshBtn = document.getElementById('refresh-chat');
    const lockBtn = document.getElementById('lock-chat-btn');
    const unlockBtn = document.getElementById('unlock-chat-btn');
    const passwordInput = document.getElementById('chat-password');
    const passwordError = document.getElementById('password-error');
    const lockScreen = document.getElementById('lock-screen');
    const chatMain = document.getElementById('chat-main');
    const typingStatus = document.getElementById('typing-status');
    const onlineStatusIndicator = document.getElementById('online-status-indicator');
    const onlineStatusText = document.getElementById('online-status-text');
    
    // State
    let currentSessionId = null;
    let lastMessageId = 0;
    let isProcessing = false;
    let pollingInterval = null;
    let typingTimer = null;
    let isTyping = false;
    let refreshTimeout = null;
    let lastSeenId = 0;
    let partnerOnline = false;
    let heartbeatInterval = null;
    
    // Get config from window
    const config = window.CHAT_CONFIG || {};
    const userType = config.userType || 'boy';
    const coupleId = config.coupleId;
    const boyName = config.boyName || 'Boy';
    const girlName = config.girlName || 'Girl';
    const isUnlocked = config.isUnlocked || false;
    const userId = config.userId;
    
    // Partner name based on user type
    const partnerName = userType === 'boy' ? girlName : boyName;
    const partnerType = userType === 'boy' ? 'girl' : 'boy';
    
    // Initialize chat if unlocked
    if (isUnlocked) {
        initializeChat();
    }
    
    // Unlock chat function
    async function unlockChat() {
        const password = passwordInput.value.trim();
        
        if (!password) {
            showError('Please enter the password');
            return;
        }
        
        // Show loading state
        const unlockBtn = document.querySelector('.unlock-btn');
        const originalText = unlockBtn.innerHTML;
        unlockBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Unlocking...</span>';
        unlockBtn.disabled = true;
        
        try {
            const response = await fetch('/api/chat/unlock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ password: password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Hide lock screen
                if (lockScreen) {
                    lockScreen.style.display = 'none';
                }
                
                // Remove blur from chat
                if (chatMain) {
                    chatMain.style.filter = 'none';
                    chatMain.style.pointerEvents = 'auto';
                }
                
                // Set session ID
                currentSessionId = data.session_id;
                
                // Initialize chat
                initializeChat();
                
                showNotification('Chat unlocked successfully!', 'success');
            } else {
                // Show error
                if (passwordError) {
                    passwordError.style.display = 'flex';
                    setTimeout(() => {
                        passwordError.style.display = 'none';
                    }, 3000);
                }
                passwordInput.value = '';
                passwordInput.focus();
            }
        } catch (error) {
            console.error('Unlock error:', error);
            showError('Failed to unlock chat. Please try again.');
        } finally {
            unlockBtn.innerHTML = originalText;
            unlockBtn.disabled = false;
        }
    }
    
    // Initialize chat (load messages and start polling)
    function initializeChat() {
        loadMessages();
        startPolling();
        startHeartbeat();
        updateOnlineStatus();
        
        // Focus input
        if (chatInput) {
            chatInput.focus();
        }
    }
    
    // Start heartbeat to track online status
    function startHeartbeat() {
        // Send heartbeat every 30 seconds
        heartbeatInterval = setInterval(sendHeartbeat, 30000);
        // Send initial heartbeat
        sendHeartbeat();
    }
    
    // Send heartbeat to server
    async function sendHeartbeat() {
        if (!currentSessionId) return;
        
        try {
            await fetch('/api/chat/heartbeat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    session_id: currentSessionId,
                    user_type: userType
                })
            });
        } catch (error) {
            console.error('Heartbeat error:', error);
        }
    }
    
    // Update online status display
    function updateOnlineStatus(isOnline) {
        if (typeof isOnline !== 'undefined') {
            partnerOnline = isOnline;
        }
        
        if (onlineStatusIndicator && onlineStatusText) {
            if (partnerOnline) {
                onlineStatusIndicator.className = 'online-status-indicator online';
                onlineStatusText.textContent = `${partnerName} is online`;
                onlineStatusText.style.color = '#4ade80';
            } else {
                onlineStatusIndicator.className = 'online-status-indicator offline';
                onlineStatusText.textContent = `${partnerName} is offline`;
                onlineStatusText.style.color = '#94a3b8';
            }
        }
    }
    
    // Mark messages as seen
    async function markMessagesAsSeen(messageIds) {
        if (!messageIds || messageIds.length === 0 || !currentSessionId) return;
        
        try {
            await fetch('/api/chat/mark-seen', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    session_id: currentSessionId,
                    message_ids: messageIds,
                    user_type: userType
                })
            });
        } catch (error) {
            console.error('Error marking messages as seen:', error);
        }
    }
    
    // Load initial messages
    async function loadMessages() {
        if (!currentSessionId) {
            // Get the first session or create one
            await getOrCreateSession();
        }
        
        if (!currentSessionId) return;
        
        try {
            const response = await fetch(`/api/chat-sessions/${currentSessionId}/messages`);
            const data = await response.json();
            
            if (data.success) {
                renderMessages(data.messages);
                
                // Update last message ID
                if (data.messages.length > 0) {
                    lastMessageId = data.messages[data.messages.length - 1].id;
                }
                
                // Mark unread messages as seen
                const unreadMessageIds = data.messages
                    .filter(msg => msg.sender_type !== userType && !msg.seen)
                    .map(msg => msg.id);
                
                if (unreadMessageIds.length > 0) {
                    markMessagesAsSeen(unreadMessageIds);
                }
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            showError('Failed to load messages');
        }
    }
    
    // Get or create a chat session
    async function getOrCreateSession() {
        try {
            const response = await fetch('/api/chat-sessions');
            const data = await response.json();
            
            if (data.success && data.sessions.length > 0) {
                // Use the most recent session
                currentSessionId = data.sessions[0].id;
            } else {
                // Create a new session
                const createResponse = await fetch('/api/chat-sessions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        title: `${boyName} & ${girlName}'s Chat` 
                    })
                });
                
                const createData = await createResponse.json();
                if (createData.success) {
                    currentSessionId = createData.session.id;
                }
            }
        } catch (error) {
            console.error('Error getting/creating session:', error);
        }
    }
    
    // Format time consistently (UTC to local)
    function formatTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true
        });
    }
    
    // Format date consistently
    function formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }
    
    // Render messages in the container
    function renderMessages(messages) {
        if (!messagesContainer) return;
        
        if (!messages || messages.length === 0) {
            messagesContainer.innerHTML = `
                <div class="message welcome-message">
                    <div class="message-avatar">
                        <i class="fas fa-heart"></i>
                    </div>
                    <div class="message-bubble">
                        <p>Start your private conversation! 💕</p>
                        <p>Send a message to your partner. Your chat is private and secure.</p>
                        <small>${boyName} ❤️ ${girlName}</small>
                    </div>
                </div>
            `;
            return;
        }
        
        let html = '';
        let lastDate = '';
        
        messages.forEach(msg => {
            // Add date separator if date changes
            const msgDate = formatDate(msg.created_at);
            if (msgDate !== lastDate) {
                lastDate = msgDate;
                html += `<div class="date-separator"><span>${msgDate}</span></div>`;
            }
            
            // Determine if message is from current user
            const isFromCurrentUser = msg.sender_type === userType;
            const messageClass = isFromCurrentUser ? 'message user-message' : 'message partner-message';
            
            // Set avatar icon
            const avatarIcon = msg.sender_type === 'boy' ? 'fa-male' : 'fa-female';
            
            // Use server-formatted time if available, otherwise format it
            const timeDisplay = msg.formatted_time || formatTime(msg.created_at);
            
            // Add seen indicator for user's own messages
            const seenIndicator = isFromCurrentUser ? 
                `<span class="message-seen-indicator ${msg.seen ? 'seen' : 'delivered'}" title="${msg.seen ? 'Seen' : 'Delivered'}">
                    <i class="fas ${msg.seen ? 'fa-check-double' : 'fa-check'}"></i>
                </span>` : '';
            
            html += `
                <div class="${messageClass}" data-message-id="${msg.id}">
                    <div class="message-avatar">
                        <i class="fas ${avatarIcon}"></i>
                    </div>
                    <div class="message-bubble">
                        <div class="message-header">
                            <span class="message-sender">${msg.display_sender_name}</span>
                        </div>
                        <div class="message-content">${escapeHtml(msg.message).replace(/\n/g, '<br>')}</div>
                        <div class="message-footer">
                            <span class="message-time">${timeDisplay}</span>
                            ${seenIndicator}
                        </div>
                    </div>
                </div>
            `;
        });
        
        messagesContainer.innerHTML = html;
        
        // Scroll to bottom
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Auto refresh page function
    function autoRefreshPage() {
        // Clear any existing timeout
        if (refreshTimeout) {
            clearTimeout(refreshTimeout);
        }
        
        // Show refresh notification
        showNotification('Refreshing chat...', 'info');
        
        // Set timeout to refresh page after 1.5 seconds
        refreshTimeout = setTimeout(() => {
            window.location.reload();
        }, 1500);
    }
    
    // Send message function
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message || isProcessing || !currentSessionId) return;
        
        // Add optimistic UI update
        addOptimisticMessage(message);
        
        // Clear input
        chatInput.value = '';
        
        // Show loading
        isProcessing = true;
        if (loadingOverlay) loadingOverlay.style.display = 'flex';
        
        try {
            const response = await fetch('/api/chat/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message,
                    session_id: currentSessionId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update last message ID
                lastMessageId = data.chat_id;
                
                // Auto refresh page after 1.5 seconds
                autoRefreshPage();
            } else {
                // Remove optimistic message on error
                removeOptimisticMessage();
                
                if (data.error === 'chat_locked') {
                    // Chat got locked, reload page
                    window.location.reload();
                } else {
                    showError(data.message || 'Failed to send message');
                }
            }
        } catch (error) {
            console.error('Send error:', error);
            removeOptimisticMessage();
            showError('Connection error. Please try again.');
        } finally {
            isProcessing = false;
            if (loadingOverlay) loadingOverlay.style.display = 'none';
        }
    }
    
    // Add optimistic message to UI
    function addOptimisticMessage(message) {
        const now = new Date();
        
        // Format time and date consistently
        const timeStr = now.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true
        });
        
        const dateStr = now.toLocaleDateString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        
        // Check if we need to add a date separator
        const lastDateSeparator = messagesContainer.querySelector('.date-separator:last-child span');
        if (!lastDateSeparator || lastDateSeparator.textContent !== dateStr) {
            messagesContainer.insertAdjacentHTML('beforeend', `<div class="date-separator"><span>${dateStr}</span></div>`);
        }
        
        const avatarIcon = userType === 'boy' ? 'fa-male' : 'fa-female';
        
        const messageHtml = `
            <div class="message user-message optimistic-message">
                <div class="message-avatar">
                    <i class="fas ${avatarIcon}"></i>
                </div>
                <div class="message-bubble">
                    <div class="message-header">
                        <span class="message-sender">You</span>
                    </div>
                    <div class="message-content">${escapeHtml(message)}</div>
                    <div class="message-footer">
                        <span class="message-time">${timeStr}</span>
                        <span class="message-seen-indicator delivered">
                            <i class="fas fa-check"></i>
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        // Remove welcome message if it exists
        const welcomeMessage = messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
        
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // Remove optimistic message (on error)
    function removeOptimisticMessage() {
        const optimisticMsg = messagesContainer.querySelector('.optimistic-message');
        if (optimisticMsg) {
            optimisticMsg.remove();
        }
    }
    
    // Start polling for new messages
    function startPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        pollingInterval = setInterval(pollMessages, 3000); // Poll every 3 seconds
    }
    
    // Poll for new messages
    async function pollMessages() {
        if (!currentSessionId) return;
        
        try {
            const response = await fetch(`/api/chat/poll?session_id=${currentSessionId}&last_message_id=${lastMessageId}`);
            const data = await response.json();
            
            if (data.success) {
                if (data.messages && data.messages.length > 0) {
                    // Append new messages to UI
                    appendNewMessages(data.messages);
                    
                    // Update last message ID
                    lastMessageId = data.last_message_id;
                    
                    // Mark new messages as seen
                    const newMessageIds = data.messages
                        .filter(msg => msg.sender_type !== userType)
                        .map(msg => msg.id);
                    
                    if (newMessageIds.length > 0) {
                        markMessagesAsSeen(newMessageIds);
                    }
                }
                
                // Update seen status for existing messages
                if (data.seen_updates && data.seen_updates.length > 0) {
                    updateSeenStatus(data.seen_updates);
                }
                
                // Update online status
                if (typeof data.partner_online !== 'undefined') {
                    updateOnlineStatus(data.partner_online);
                }
            }
        } catch (error) {
            console.error('Poll error:', error);
        }
    }
    
    // Update seen status for messages
    function updateSeenStatus(seenUpdates) {
        seenUpdates.forEach(update => {
            const messageElement = document.querySelector(`.message[data-message-id="${update.message_id}"]`);
            if (messageElement) {
                const seenIndicator = messageElement.querySelector('.message-seen-indicator');
                if (seenIndicator) {
                    seenIndicator.className = 'message-seen-indicator seen';
                    seenIndicator.innerHTML = '<i class="fas fa-check-double"></i>';
                    seenIndicator.title = 'Seen';
                }
            }
        });
    }
    
    // Append new messages to UI
    function appendNewMessages(messages) {
        let html = '';
        let lastDate = '';
        
        // Get the last date from existing messages
        const lastDateSeparator = messagesContainer.querySelector('.date-separator:last-child span');
        if (lastDateSeparator) {
            lastDate = lastDateSeparator.textContent;
        }
        
        messages.forEach(msg => {
            // Add date separator if date changes
            const msgDate = formatDate(msg.created_at);
            if (msgDate !== lastDate) {
                lastDate = msgDate;
                html += `<div class="date-separator"><span>${msgDate}</span></div>`;
            }
            
            const isFromCurrentUser = msg.sender_type === userType;
            const messageClass = isFromCurrentUser ? 'message user-message' : 'message partner-message';
            const avatarIcon = msg.sender_type === 'boy' ? 'fa-male' : 'fa-female';
            
            // Use server-formatted time if available, otherwise format it
            const timeDisplay = msg.formatted_time || formatTime(msg.created_at);
            
            // Add seen indicator for user's own messages
            const seenIndicator = isFromCurrentUser ? 
                `<span class="message-seen-indicator ${msg.seen ? 'seen' : 'delivered'}" title="${msg.seen ? 'Seen' : 'Delivered'}">
                    <i class="fas ${msg.seen ? 'fa-check-double' : 'fa-check'}"></i>
                </span>` : '';
            
            html += `
                <div class="${messageClass}" data-message-id="${msg.id}">
                    <div class="message-avatar">
                        <i class="fas ${avatarIcon}"></i>
                    </div>
                    <div class="message-bubble">
                        <div class="message-header">
                            <span class="message-sender">${msg.display_sender_name}</span>
                        </div>
                        <div class="message-content">${escapeHtml(msg.message).replace(/\n/g, '<br>')}</div>
                        <div class="message-footer">
                            <span class="message-time">${timeDisplay}</span>
                            ${seenIndicator}
                        </div>
                    </div>
                </div>
            `;
        });
        
        if (html) {
            // Remove optimistic messages (they will be replaced by real ones)
            const optimisticMessages = messagesContainer.querySelectorAll('.optimistic-message');
            optimisticMessages.forEach(msg => msg.remove());
            
            messagesContainer.insertAdjacentHTML('beforeend', html);
            
            messagesContainer.scrollTo({
                top: messagesContainer.scrollHeight,
                behavior: 'smooth'
            });
            
            // Play notification sound for partner messages
            const lastMsg = messages[messages.length - 1];
            if (lastMsg && lastMsg.sender_type !== userType) {
                playNotificationSound();
            }
        }
    }
    
    // Play notification sound (if browser supports it)
    function playNotificationSound() {
        try {
            // Simple beep using Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 523.25; // C5 note
            gainNode.gain.value = 0.1;
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
            
            // Resume audio context if it's suspended (browser autoplay policy)
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
        } catch (e) {
            // Ignore audio errors
        }
    }
    
    // Lock chat
    function lockChat() {
        // Clear polling
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        
        // Clear heartbeat
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
        
        // Clear refresh timeout if exists
        if (refreshTimeout) {
            clearTimeout(refreshTimeout);
            refreshTimeout = null;
        }
        
        // Reload page to show lock screen
        window.location.reload();
    }
    
    // Show error message
    function showError(message) {
        if (passwordError) {
            passwordError.querySelector('span').textContent = message;
            passwordError.style.display = 'flex';
            setTimeout(() => {
                passwordError.style.display = 'none';
            }, 3000);
        } else {
            showNotification(message, 'error');
        }
    }
    
    // Show notification
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        let icon = 'fa-info-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';
        if (type === 'success') icon = 'fa-check-circle';
        
        notification.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Handle typing indicator
    if (chatInput) {
        chatInput.addEventListener('input', () => {
            if (!isTyping) {
                isTyping = true;
                // Send typing indicator
                fetch('/api/chat/typing', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        session_id: currentSessionId,
                        is_typing: true,
                        user_type: userType
                    })
                }).catch(err => console.error('Typing indicator error:', err));
            }
            
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                isTyping = false;
                // Send stopped typing
                fetch('/api/chat/typing', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        session_id: currentSessionId,
                        is_typing: false,
                        user_type: userType
                    })
                }).catch(err => console.error('Typing indicator error:', err));
                
                if (typingStatus) {
                    typingStatus.textContent = '';
                }
            }, 1000);
        });
    }
    
    // Event Listeners
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    if (unlockBtn) {
        unlockBtn.addEventListener('click', unlockChat);
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                unlockChat();
            }
        });
    }
    
    if (lockBtn) {
        lockBtn.addEventListener('click', lockChat);
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadMessages();
            showNotification('Chat refreshed', 'success');
        });
    }
    
    // Handle online/offline status
    window.addEventListener('online', () => {
        showNotification('You are back online!', 'success');
        if (isUnlocked) {
            loadMessages();
            startHeartbeat();
        }
    });
    
    window.addEventListener('offline', () => {
        showNotification('You are offline. Messages will be sent when you reconnect.', 'error');
        updateOnlineStatus(false);
    });
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
        }
        if (refreshTimeout) {
            clearTimeout(refreshTimeout);
        }
    });
});