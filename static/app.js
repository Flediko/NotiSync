// NotiSync Client Application Logic

let socket = null;
let reconnectTimer = null;
let notifications = []; // Local storage of notifications

// DOM Elements
const statusBadge = document.getElementById('status-badge');
const statusText = document.getElementById('status-text');
const notificationsList = document.getElementById('notifications-list');
const emptyState = document.getElementById('empty-state');
const countBadge = document.getElementById('count-badge');
const searchInput = document.getElementById('search-input');
const soundToggle = document.getElementById('sound-toggle');

// Modal Elements
const detailModal = document.getElementById('detail-modal');
const modalAppBadge = document.getElementById('modal-app-badge');
const modalTime = document.getElementById('modal-time');
const modalClose = document.getElementById('modal-close');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const modalBtnCopy = document.getElementById('modal-btn-copy');
const modalBtnDismiss = document.getElementById('modal-btn-dismiss');

// Scanner Elements
const btnScanQr = document.getElementById('btn-scan-qr');
const scannerModal = document.getElementById('scanner-modal');
const scannerClose = document.getElementById('scanner-close');

// Initialize Connection on Load
window.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    
    // Setup Search Event Listener
    searchInput.addEventListener('input', () => {
        renderNotifications();
    });
    
    // Register PWA Service Worker (only if running as standard web app in browser)
    if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
        navigator.serviceWorker.register('static/sw.js')
            .then(() => console.log('PWA Service Worker Registered.'))
            .catch(err => console.error('PWA Service Worker registration failed:', err));
    }

    // Request notification permission on startup (for native/PWA alerts)
    if (window.Notification && Notification.permission !== 'granted') {
        Notification.requestPermission()
            .then(perm => console.log('Notification permission state:', perm))
            .catch(err => console.error('Error requesting notification permission:', err));
    }

    // Setup Modal Close Event Listeners
    modalClose.addEventListener('click', closeNotificationDetail);
    
    // Close modal by clicking outside the modal content card
    detailModal.addEventListener('click', (e) => {
        if (e.target === detailModal) {
            closeNotificationDetail();
        }
    });

    // Setup Scanner Event Listeners
    btnScanQr.addEventListener('click', openQRScanner);
    scannerClose.addEventListener('click', closeQRScanner);
    
    // Close scanner modal by clicking outside
    scannerModal.addEventListener('click', (e) => {
        if (e.target === scannerModal) {
            closeQRScanner();
        }
    });

    // Setup Pairing / Setup Screen Events
    const btnSetupScan = document.getElementById('btn-setup-scan');
    const btnSetupConnect = document.getElementById('btn-setup-connect');
    const setupUrlInput = document.getElementById('setup-url-input');
    const btnDisconnect = document.getElementById('btn-disconnect');

    if (btnSetupScan) btnSetupScan.addEventListener('click', openQRScanner);
    
    if (btnSetupConnect) {
        btnSetupConnect.addEventListener('click', () => {
            const url = setupUrlInput.value.trim();
            if (url) {
                let formattedUrl = url;
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    formattedUrl = 'http://' + url;
                }
                localStorage.setItem('server_url', formattedUrl);
                connectWebSocket();
            } else {
                alert('Please enter a valid server IP or URL.');
            }
        });
    }

    if (setupUrlInput) {
        setupUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                btnSetupConnect.click();
            }
        });
    }

    if (btnDisconnect) {
        btnDisconnect.addEventListener('click', () => {
            if (confirm('Disconnect from laptop? You will need to scan the QR code to connect again.')) {
                disconnectServer();
            }
        });
    }

    // Close modals with Escape key
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (detailModal.classList.contains('active')) {
                closeNotificationDetail();
            }
            if (scannerModal.classList.contains('active')) {
                closeQRScanner();
            }
        }
    });
});

// WebSocket Connection Management
function connectWebSocket() {
    clearTimeout(reconnectTimer);
    
    const serverUrl = getServerUrl();
    if (!serverUrl) {
        showSetupView();
        return;
    }
    
    hideSetupView();
    
    // Convert HTTP(S) URL to WebSocket protocol WS(S)
    let wsUrl = serverUrl.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/$/, '') + '/ws';
    }
    
    updateStatus('connecting', 'Connecting...');
    
    try {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            console.log('WebSocket connection established.');
            
            // Format a simple status text containing server host
            try {
                const urlObj = new URL(serverUrl);
                updateStatus('connected', `Live Sync (${urlObj.hostname})`);
            } catch (e) {
                updateStatus('connected', 'Live Sync');
            }

            // Start native background service if running inside Capacitor
            if (window.Capacitor && window.Capacitor.Plugins.NotificationService) {
                window.Capacitor.Plugins.NotificationService.startService({ serverUrl: serverUrl })
                    .then(res => console.log('Native background service active:', res))
                    .catch(err => console.error('Failed to start native background service:', err));
            }
        };
        
        socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleServerMessage(message);
            } catch (e) {
                console.error('Error parsing message: ', e);
            }
        };
        
        socket.onclose = (event) => {
            console.warn('WebSocket connection closed. Code:', event.code);
            updateStatus('disconnected', 'Disconnected');
            scheduleReconnect();
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateStatus('disconnected', 'Connection Error');
        };
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateStatus('disconnected', 'Setup Failed');
        scheduleReconnect();
    }
}

function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
        console.log('Attempting to reconnect...');
        connectWebSocket();
    }, 3000); // Retry every 3 seconds
}

function updateStatus(state, text) {
    statusBadge.className = `status-badge state-${state}`;
    statusText.textContent = text;
    
    // Manage header disconnect button visibility
    const btnDisconnect = document.getElementById('btn-disconnect');
    if (btnDisconnect) {
        if (localStorage.getItem('server_url')) {
            btnDisconnect.style.display = 'flex';
        } else {
            btnDisconnect.style.display = 'none';
        }
    }
}

// Router for server WebSocket events
function handleServerMessage(msg) {
    switch (msg.type) {
        case 'sync':
            // Initial load or full sync
            notifications = msg.notifications || [];
            renderNotifications();
            break;
            
        case 'added':
            // Check if notification already exists to avoid duplicates
            if (!notifications.some(n => n.id === msg.notification.id)) {
                notifications.unshift(msg.notification); // Add new at top
                renderNotifications();
                playChime();
            }
            break;
            
        case 'removed':
            // Animate card removal before rendering
            animateCardRemoval(msg.id);
            break;
            
        default:
            console.log('Unknown message type:', msg.type);
    }
}

// Web Audio API Synthesized Chime Alert
function playChime() {
    if (!soundToggle.checked) return;
    
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        
        // Note 1: High soft bell note
        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
        gain1.gain.setValueAtTime(0.06, audioCtx.currentTime);
        gain1.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        
        // Note 2: Higher harmonized chime note (slightly delayed)
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1174.66, audioCtx.currentTime + 0.08); // D6 note
        gain2.gain.setValueAtTime(0, audioCtx.currentTime);
        gain2.gain.setValueAtTime(0.06, audioCtx.currentTime + 0.08);
        gain2.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        
        // Start and stop
        osc1.start();
        osc1.stop(audioCtx.currentTime + 0.4);
        
        osc2.start(audioCtx.currentTime + 0.08);
        osc2.stop(audioCtx.currentTime + 0.55);
    } catch (e) {
        console.warn('Web Audio API is blocked or unsupported by this browser:', e);
    }
}

// Render loop for UI (DOM Diffing/Patching approach to prevent flickering)
function renderNotifications() {
    const searchFilter = searchInput.value.toLowerCase().trim();
    
    // Filter notifications based on search query
    const filtered = notifications.filter(n => {
        if (!searchFilter) return true;
        const app = (n.app_name || '').toLowerCase();
        const title = (n.title || '').toLowerCase();
        const body = (n.body || '').toLowerCase();
        return app.includes(searchFilter) || title.includes(searchFilter) || body.includes(searchFilter);
    });

    // Update count badge
    countBadge.textContent = filtered.length;

    // Toggle Empty State view
    if (filtered.length === 0) {
        emptyState.style.display = 'flex';
        notificationsList.style.display = 'none';
        notificationsList.innerHTML = '';
        return;
    } else {
        emptyState.style.display = 'none';
        notificationsList.style.display = 'flex';
    }

    // Capture currently rendered cards in DOM
    const currentCardsMap = new Map();
    Array.from(notificationsList.children).forEach(child => {
        const id = parseInt(child.dataset.id);
        currentCardsMap.set(id, child);
    });

    // Create a set of IDs that should be visible
    const newIds = new Set(filtered.map(n => n.id));

    // Remove cards that are no longer in the new list (with exit animation)
    currentCardsMap.forEach((card, id) => {
        if (!newIds.has(id) && !card.classList.contains('removing')) {
            card.classList.add('removing');
            card.addEventListener('animationend', () => {
                card.remove();
                if (notificationsList.children.length === 0) {
                    emptyState.style.display = 'flex';
                    notificationsList.style.display = 'none';
                }
            });
        }
    });

    // Add or reorder cards to match the filtered list order
    filtered.forEach((n, index) => {
        let card = currentCardsMap.get(n.id);
        
        if (!card) {
            // Build new card
            card = document.createElement('div');
            card.className = 'notification-card';
            card.dataset.id = n.id;
            card.innerHTML = `
                <div class="card-content">
                    <div class="card-meta">
                        <span class="app-badge">${escapeHTML(n.app_name)}</span>
                        <span class="card-time">${escapeHTML(n.timestamp)}</span>
                    </div>
                    <h3 class="card-title">${escapeHTML(n.title)}</h3>
                    <p class="card-body">${escapeHTML(n.body)}</p>
                </div>
                <button class="btn-dismiss" title="Dismiss Notification">
                    <svg viewBox="0 0 24 24">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            `;

            // Card body click handler - open details modal
            card.querySelector('.card-content').addEventListener('click', () => {
                showNotificationDetail(n);
            });

            // Dismiss Button Click Handler
            const dismissBtn = card.querySelector('.btn-dismiss');
            dismissBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Avoid triggering open modal click
                requestDismissal(n.id);
            });
        }
        
        // Insert card at correct position to match sorted index
        const referenceNode = notificationsList.children[index];
        if (referenceNode !== card) {
            notificationsList.insertBefore(card, referenceNode || null);
        }
    });
}

// Request to dismiss a notification
function requestDismissal(id) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: 'dismiss',
            id: id
        }));
    }
}

let activeDetailNotificationId = null;

// Modal dialog display handlers
function showNotificationDetail(n) {
    activeDetailNotificationId = n.id;
    modalAppBadge.textContent = n.app_name;
    modalTime.textContent = n.timestamp;
    modalTitle.textContent = n.title;
    modalBody.textContent = n.body;
    
    // Copy to clipboard handler
    modalBtnCopy.onclick = () => {
        const textToCopy = `[${n.app_name}] ${n.title}\n${n.body}`;
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const originalText = modalBtnCopy.textContent;
                modalBtnCopy.textContent = 'Copied!';
                modalBtnCopy.style.background = 'rgba(0, 230, 118, 0.1)';
                modalBtnCopy.style.color = 'var(--accent-green)';
                setTimeout(() => {
                    modalBtnCopy.textContent = originalText;
                    modalBtnCopy.style.background = '';
                    modalBtnCopy.style.color = '';
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy: ', err);
            });
    };

    // Modal dismiss button handler
    modalBtnDismiss.onclick = () => {
        requestDismissal(n.id);
        closeNotificationDetail();
    };

    detailModal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Stop background page scrolling
}

function closeNotificationDetail() {
    detailModal.classList.remove('active');
    document.body.style.overflow = ''; // Unlock background scrolling
    activeDetailNotificationId = null;
}

// Handle card exit animation before removing from local storage
function animateCardRemoval(id) {
    // If the currently open modal's notification is dismissed, close the modal smoothly
    if (activeDetailNotificationId === id) {
        closeNotificationDetail();
    }
    
    // Filter the notifications list immediately so that subsequent layout renders ignore it
    notifications = notifications.filter(n => n.id !== id);
    
    const card = notificationsList.querySelector(`.notification-card[data-id="${id}"]`);
    if (card) {
        card.classList.add('removing');
        card.addEventListener('animationend', () => {
            card.remove();
            // Re-render list layout to ensure empty state and spacing update correctly
            renderNotifications();
        });
    } else {
        renderNotifications();
    }
}

// Utility to escape HTML
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

let html5QrScanner = null;

// Camera Scanner Open Handler
function openQRScanner() {
    scannerModal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Stop background scrolling
    
    try {
        html5QrScanner = new Html5Qrcode("reader");
        html5QrScanner.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 220, height: 220 }
            },
            (decodedText) => {
                console.log(`Scan Success: ${decodedText}`);
                closeQRScanner();
                handleScannedUrl(decodedText);
            },
            (errorMessage) => {
                // Ignore silent scanner errors
            }
        ).catch(err => {
            console.error("Camera start failed: ", err);
            document.getElementById('reader').innerHTML = `<p style="color: var(--accent-red); padding: 20px;">Camera access failed. Please ensure browser has camera permission.</p>`;
        });
    } catch (e) {
        console.error("Scanner setup failed: ", e);
    }
}

// Camera Scanner Close Handler
function closeQRScanner() {
    if (html5QrScanner) {
        html5QrScanner.stop().then(() => {
            html5QrScanner = null;
        }).catch(err => {
            console.warn("Failed to stop scanner camera: ", err);
            html5QrScanner = null;
        });
    }
    scannerModal.classList.remove('active');
    document.body.style.overflow = ''; // Unlock background scrolling
}

// Dynamic pairing and navigation helper functions
function getServerUrl() {
    // 1. Return user configured pairing address if available
    const saved = localStorage.getItem('server_url');
    if (saved) return saved;
    
    // 2. Default to current window origin if running on a real web server
    if (window.location.protocol.startsWith('http')) {
        return window.location.origin;
    }
    
    return null;
}

function handleScannedUrl(decodedText) {
    if (decodedText.startsWith('http://') || decodedText.startsWith('https://')) {
        const isCapacitor = !!window.Capacitor;
        if (isCapacitor) {
            // Save server address and reconnect WebSocket inline
            localStorage.setItem('server_url', decodedText);
            connectWebSocket();
        } else {
            // Browser PWA mode: reload/redirect browser to the host domain to update PWA workspace scope
            window.location.href = decodedText;
        }
    } else {
        alert("Invalid QR code scanned: " + decodedText);
    }
}

function showSetupView() {
    const setupView = document.getElementById('setup-view');
    const appContainer = document.getElementById('app-container');
    if (setupView) setupView.style.display = 'flex';
    if (appContainer) appContainer.style.display = 'none';
}

function hideSetupView() {
    const setupView = document.getElementById('setup-view');
    const appContainer = document.getElementById('app-container');
    if (setupView) setupView.style.display = 'none';
    if (appContainer) appContainer.style.display = 'flex';
}

function disconnectServer() {
    if (socket) {
        socket.close();
    }

    // Stop native background service if running inside Capacitor
    if (window.Capacitor && window.Capacitor.Plugins.NotificationService) {
        window.Capacitor.Plugins.NotificationService.stopService()
            .then(res => console.log('Native background service stopped:', res))
            .catch(err => console.error('Failed to stop native background service:', err));
    }

    localStorage.removeItem('server_url');
    notifications = [];
    renderNotifications();
    showSetupView();
}
