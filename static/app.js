// Clean Teaching AI Validator Frontend JavaScript

class TeachingAIValidator {
    constructor() {
        this.currentTopic = '';
        this.sessionActive = false;
        this.currentView = 'welcome';
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeElements();
        this.setupAnimations();
    }

    bindEvents() {
        // Back button functionality
        document.getElementById('back-btn')?.addEventListener('click', () => {
            this.handleBackButton();
        });

        // Topic input and start button
        document.getElementById('topic-input')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.startTeachingSession();
            }
        });

        document.getElementById('start-teaching-btn')?.addEventListener('click', () => {
            this.startTeachingSession();
        });

        // Teaching input
        document.getElementById('teaching-input')?.addEventListener('input', (e) => {
            this.updateCharCounter(e.target.value);
        });

        document.getElementById('teaching-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendExplanation();
            }
        });

        document.getElementById('send-explanation-btn')?.addEventListener('click', () => {
            this.sendExplanation();
        });

        // Session controls
        document.getElementById('reset-session-btn')?.addEventListener('click', () => {
            this.resetSession();
        });

        document.getElementById('new-topic-btn')?.addEventListener('click', () => {
            this.showWelcomeScreen();
        });

        // Quick start cards
        document.querySelectorAll('.quick-card').forEach(card => {
            card.addEventListener('click', () => {
                const topic = card.dataset.topic;
                this.startQuickTopic(topic);
            });
        });

        // Topic suggestions
        document.querySelectorAll('.topic-item').forEach(item => {
            item.addEventListener('click', () => {
                const topic = item.dataset.topic;
                this.startQuickTopic(topic);
            });
        });
    }

    initializeElements() {
        // Initialize character counter
        this.updateCharCounter('');
        
        // Set initial focus
        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            setTimeout(() => topicInput.focus(), 100);
        }
    }

    setupAnimations() {
        // Add fade-in animation to main content
        const mainView = document.getElementById('main-view');
        if (mainView) {
            mainView.classList.add('fade-in');
        }
    }

    handleBackButton() {
        if (this.currentView === 'teaching') {
            // Go back to welcome screen from teaching session
            this.showWelcomeScreen();
        } else {
            // Already on welcome screen, show message
            this.showInfo('You are already on the main screen');
        }
    }

    async startTeachingSession() {
        const topicInput = document.getElementById('topic-input');
        const topic = topicInput.value.trim();

        if (!topic) {
            this.showError('Please enter a topic to teach');
            return;
        }

        this.showLoading('Starting teaching session...');

        try {
            const response = await fetch('/start_teaching', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic: topic })
            });

            const data = await response.json();

            if (response.ok) {
                this.currentTopic = topic;
                this.sessionActive = true;
                this.showTeachingSession(data);
                this.addMessage('ai', data.ai_response);
            } else {
                this.showError(data.error || 'Failed to start teaching session');
            }
        } catch (error) {
            console.error('Error starting session:', error);
            this.showError('Failed to connect to the server');
        } finally {
            this.hideLoading();
        }
    }

    async sendExplanation() {
        const teachingInput = document.getElementById('teaching-input');
        const explanation = teachingInput.value.trim();

        if (!explanation) {
            this.showError('Please provide an explanation');
            return;
        }

        if (!this.sessionActive) {
            this.showError('No active teaching session');
            return;
        }

        // Add user message immediately
        this.addMessage('user', explanation);
        teachingInput.value = '';
        this.updateCharCounter('');

        // Show typing indicator
        this.showAITyping();

        try {
            const response = await fetch('/teach_step', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ explanation: explanation })
            });

            const data = await response.json();

            if (response.ok) {
                // Update session statistics
                this.updateSessionStats(data);
                
                // Add AI response
                this.addMessage('ai', data.ai_response);
                
                // Show quality feedback
                this.showQualityFeedback(data.quality_score);
            } else {
                this.showError(data.error || 'Failed to process explanation');
            }
        } catch (error) {
            console.error('Error sending explanation:', error);
            this.showError('Failed to send explanation');
        } finally {
            this.hideAITyping();
        }
    }

    startQuickTopic(topic) {
        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.value = topic;
            this.startTeachingSession();
        }
    }

    showTeachingSession(data) {
        this.currentView = 'teaching';
        
        // Hide welcome screen
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }

        // Show teaching session
        const teachingSession = document.getElementById('teaching-session');
        if (teachingSession) {
            teachingSession.style.display = 'flex';
            teachingSession.classList.add('fade-in');
        }

        // Update topic display
        const currentTopicEl = document.getElementById('current-topic');
        if (currentTopicEl) {
            currentTopicEl.textContent = this.currentTopic;
        }

        // Clear previous messages
        this.clearMessages();

        // Focus on teaching input
        const teachingInput = document.getElementById('teaching-input');
        if (teachingInput) {
            setTimeout(() => teachingInput.focus(), 100);
        }
    }

    showWelcomeScreen() {
        this.currentView = 'welcome';
        this.sessionActive = false;
        
        // Show welcome screen
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'block';
            welcomeScreen.classList.add('fade-in');
        }

        // Hide teaching session
        const teachingSession = document.getElementById('teaching-session');
        if (teachingSession) {
            teachingSession.style.display = 'none';
        }

        // Reset topic input
        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.value = '';
            setTimeout(() => topicInput.focus(), 100);
        }
    }

    addMessage(type, content) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;

        const avatarEl = document.createElement('div');
        avatarEl.className = 'message-avatar';
        avatarEl.innerHTML = type === 'ai' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.textContent = content;

        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        contentEl.appendChild(textEl);
        contentEl.appendChild(timeEl);
        messageEl.appendChild(avatarEl);
        messageEl.appendChild(contentEl);

        chatMessages.appendChild(messageEl);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Add animation
        messageEl.style.opacity = '0';
        messageEl.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            messageEl.style.opacity = '1';
            messageEl.style.transform = 'translateY(0)';
            messageEl.style.transition = 'all 0.3s ease';
        }, 50);
    }

    clearMessages() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
    }

    showAITyping() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const typingEl = document.createElement('div');
        typingEl.className = 'message ai typing-indicator';
        typingEl.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        chatMessages.appendChild(typingEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    hideAITyping() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    updateCharCounter(text) {
        const charCount = document.getElementById('char-count');
        if (charCount) {
            charCount.textContent = text.length;
            
            // Change color based on character count
            if (text.length > 900) {
                charCount.style.color = '#ff5555';
            } else if (text.length > 700) {
                charCount.style.color = '#ffb86c';
            } else {
                charCount.style.color = 'rgba(255, 255, 255, 0.5)';
            }
        }
    }

    updateSessionStats(data) {
        // Update teaching quality
        const qualityEl = document.getElementById('teaching-quality');
        if (qualityEl && data.quality_score !== undefined) {
            qualityEl.textContent = data.quality_score.toFixed(2);
        }

        // Update AI level
        const aiLevelEl = document.getElementById('ai-level');
        if (aiLevelEl && data.session_progress?.confusion_level !== undefined) {
            aiLevelEl.textContent = data.session_progress.confusion_level;
        }

        // Update exchanges count
        const exchangesEl = document.getElementById('exchanges-count');
        if (exchangesEl && data.exchanges_count !== undefined) {
            exchangesEl.textContent = data.exchanges_count;
        }

        // Update user score (example calculation)
        const userScoreEl = document.getElementById('user-score');
        if (userScoreEl && data.session_progress?.average_quality !== undefined) {
            const score = Math.round(data.session_progress.average_quality * 100);
            userScoreEl.textContent = score;
        }
    }

    showQualityFeedback(score) {
        // Create temporary feedback element
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'quality-feedback';
        
        let message = '';
        let color = '';
        
        if (score >= 0.8) {
            message = 'Excellent explanation!';
            color = '#10b981';
        } else if (score >= 0.6) {
            message = 'Good explanation!';
            color = '#3b82f6';
        } else if (score >= 0.4) {
            message = 'Could use more detail';
            color = '#f59e0b';
        } else {
            message = 'Try explaining with examples';
            color = '#ef4444';
        }

        feedbackEl.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${color};
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                z-index: 1000;
                animation: slideInRight 0.3s ease;
            ">
                ${message}
            </div>
        `;

        document.body.appendChild(feedbackEl);

        // Remove after 3 seconds
        setTimeout(() => {
            feedbackEl.remove();
        }, 3000);
    }

    async resetSession() {
        if (!this.sessionActive) return;

        try {
            const response = await fetch('/reset_session', {
                method: 'POST'
            });

            if (response.ok) {
                this.clearMessages();
                this.updateSessionStats({ 
                    quality_score: 0, 
                    exchanges_count: 0, 
                    session_progress: { confusion_level: 1, average_quality: 0 } 
                });
                this.showSuccess('Session reset successfully');
            }
        } catch (error) {
            console.error('Error resetting session:', error);
            this.showError('Failed to reset session');
        }
    }

    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.querySelector('p').textContent = message;
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type = 'info') {
        const colors = {
            error: '#ef4444',
            success: '#10b981',
            info: '#3b82f6'
        };

        const notification = document.createElement('div');
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${colors[type]};
                color: white;
                padding: 16px 24px;
                border-radius: 12px;
                font-weight: 500;
                z-index: 1001;
                max-width: 400px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                animation: slideInRight 0.3s ease;
            ">
                ${message}
            </div>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
}

// Add CSS animations dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .typing-dots {
        display: flex;
        gap: 4px;
        padding: 8px 0;
    }

    .typing-dots span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        animation: typingDot 1.4s infinite ease-in-out;
    }

    .typing-dots span:nth-child(2) {
        animation-delay: 0.2s;
    }

    .typing-dots span:nth-child(3) {
        animation-delay: 0.4s;
    }

    @keyframes typingDot {
        0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }

    /* Smooth transitions */
    .quick-card, .topic-item, .control-btn {
        transition: all 0.2s ease !important;
    }

    /* Focus styles */
    input:focus, textarea:focus, select:focus {
        outline: none !important;
    }

    /* Custom scrollbar for webkit browsers */
    ::-webkit-scrollbar {
        width: 6px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
`;
document.head.appendChild(style);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.teachingAI = new TeachingAIValidator();
    console.log('Teaching AI Validator initialized!');
});

// Handle page visibility for better UX
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Refresh focus when page becomes visible
        if (window.teachingAI?.currentView === 'welcome') {
            const topicInput = document.getElementById('topic-input');
            if (topicInput) setTimeout(() => topicInput.focus(), 100);
        }
    }
});