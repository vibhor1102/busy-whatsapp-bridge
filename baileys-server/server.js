const express = require('express');
const QRCode = require('qrcode');
const path = require('path');
const BaileysClient = require('./baileys-client');

const app = express();
const PORT = process.env.BAILEYS_PORT || 3001;
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || path.join(__dirname, 'auth', 'baileys_session');

app.use(express.json());

// Store connected SSE clients
const sseClients = new Set();

// Helper to broadcast to all SSE clients
function broadcastSSE(data) {
    const message = `data: ${JSON.stringify(data)}\n\n`;
    sseClients.forEach(client => {
        try {
            client.write(message);
        } catch (e) {
            // Client disconnected
            sseClients.delete(client);
        }
    });
}

const client = new BaileysClient({
    authDir: AUTH_DIR,
    logLevel: process.env.BAILEYS_LOG_LEVEL || 'info'
});

client.on('qr', async (qr) => {
    console.log('[QR] New QR code generated');
    // Generate QR image and broadcast immediately
    try {
        const qrImage = await QRCode.toDataURL(qr, { width: 300, margin: 2 });
        broadcastSSE({
            type: 'qr',
            qrImage: qrImage,
            timestamp: Date.now()
        });
    } catch (err) {
        console.error('[ERROR] Failed to generate QR for SSE:', err.message);
    }
});

client.on('connected', (data) => {
    console.log('[CONNECTED]', data);
    broadcastSSE({
        type: 'connected',
        user: data
    });
});

client.on('logout', () => {
    console.log('[LOGOUT] Device logged out');
    broadcastSSE({
        type: 'logout'
    });
});

client.on('reconnecting', (data) => {
    console.log('[RECONNECTING]', data);
    broadcastSSE({
        type: 'reconnecting',
        data: data
    });
});

app.get('/status', (req, res) => {
    const status = client.getStatus();
    res.json({
        success: true,
        data: status
    });
});

app.get('/qr', async (req, res) => {
    try {
        const qrData = client.getQRCode();
        
        if (!qrData || qrData.isExpired) {
            const status = client.getStatus();
            if (status.state === 'connected') {
                return res.json({
                    success: true,
                    message: 'Already connected',
                    data: {
                        state: 'connected',
                        user: status.user
                    }
                });
            }
            return res.status(404).json({
                success: false,
                error: qrData?.isExpired ? 'QR code expired, generating new one...' : 'QR code not available. Connection may be in progress.',
                data: status
            });
        }

        const qrImage = await QRCode.toDataURL(qrData.qr, {
            width: 400,
            margin: 2,
            color: {
                dark: '#000000',
                light: '#ffffff'
            }
        });

        res.json({
            success: true,
            data: {
                qrImage: qrImage,
                timestamp: qrData.timestamp,
                expiresIn: qrData.expiresIn,
                age: qrData.age,
                isExpired: false
            }
        });
    } catch (error) {
        console.error('[ERROR] Failed to generate QR image:', error.message);
        res.status(500).json({
            success: false,
            error: 'Failed to generate QR image',
            details: error.message
        });
    }
});

app.get('/qr/page', (req, res) => {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp QR Code - Busy Gateway</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        h1 {
            color: #25D366;
            font-size: 24px;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .status-connected { background: #d4edda; color: #155724; }
        .status-qr_ready { background: #fff3cd; color: #856404; }
        .status-disconnected { background: #f8d7da; color: #721c24; }
        .qr-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            min-height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .qr-container img {
            max-width: 280px;
            height: auto;
        }
        .qr-placeholder {
            font-size: 48px;
            color: #ccc;
        }
        .stopwatch {
            font-family: 'Courier New', monospace;
            font-size: 32px;
            font-weight: bold;
            color: #856404;
            background: #fff3cd;
            padding: 10px 20px;
            border-radius: 10px;
            margin: 15px 0;
            display: inline-block;
        }
        .stopwatch-label {
            font-size: 12px;
            color: #856404;
            margin-top: 5px;
        }
        .info {
            color: #6c757d;
            font-size: 13px;
            line-height: 1.6;
        }
        .info strong { color: #495057; }
        .user-info {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .user-info p {
            margin: 5px 0;
            color: #2e7d32;
        }
        .connection-status {
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
        }
        .connection-status.connecting {
            background: #e3f2fd;
            color: #1976d2;
        }
        .connection-status.reconnecting {
            background: #fff3e0;
            color: #f57c00;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 id="title">Connecting...</h1>
        <p class="subtitle" id="subtitle">Please wait</p>
        <span class="status-badge status-disconnected" id="status-badge">Initializing</span>
        
        <div class="qr-container" id="qr-container">
            <span class="qr-placeholder">⟳</span>
        </div>
        
        <div id="stopwatch-section" style="display: none;">
            <div class="stopwatch" id="stopwatch">00.00</div>
            <div class="stopwatch-label">seconds since QR generated</div>
        </div>
        
        <div class="info" id="info-section">
            <p>Initializing WhatsApp connection...</p>
        </div>
        
        <div class="connection-status connecting" id="connection-status">
            Waiting for server connection...
        </div>
    </div>

    <script>
        let lastQRTime = null;
        let stopwatchInterval = null;
        let eventSource = null;
        
        function startStopwatch() {
            if (stopwatchInterval) clearInterval(stopwatchInterval);
            lastQRTime = Date.now();
            
            stopwatchInterval = setInterval(() => {
                if (lastQRTime) {
                    const elapsed = (Date.now() - lastQRTime) / 1000;
                    document.getElementById('stopwatch').textContent = elapsed.toFixed(2);
                }
            }, 10);
        }
        
        function stopStopwatch() {
            if (stopwatchInterval) {
                clearInterval(stopwatchInterval);
                stopwatchInterval = null;
            }
        }
        
        function updateQRState(type, data) {
            const title = document.getElementById('title');
            const subtitle = document.getElementById('subtitle');
            const badge = document.getElementById('status-badge');
            const qrContainer = document.getElementById('qr-container');
            const stopwatchSection = document.getElementById('stopwatch-section');
            const infoSection = document.getElementById('info-section');
            const statusEl = document.getElementById('connection-status');
            
            if (type === 'qr') {
                // New QR code received
                title.textContent = 'Scan QR Code';
                subtitle.textContent = 'Use WhatsApp on your phone to scan';
                badge.textContent = 'Waiting for Scan';
                badge.className = 'status-badge status-qr_ready';
                qrContainer.innerHTML = '<img src="' + data.qrImage + '" alt="WhatsApp QR Code" style="max-width: 280px;">';
                stopwatchSection.style.display = 'block';
                infoSection.innerHTML = '<p><strong>How to connect:</strong></p><p>1. Open WhatsApp on your phone</p><p>2. Go to Settings > Linked Devices</p><p>3. Tap "Link a Device"</p><p>4. Point your phone at this screen</p>';
                statusEl.style.display = 'none';
                startStopwatch();
            } else if (type === 'connected') {
                // Connected successfully
                title.textContent = 'Connected!';
                subtitle.textContent = 'WhatsApp Web is ready';
                badge.textContent = 'Connected';
                badge.className = 'status-badge status-connected';
                qrContainer.innerHTML = '<div class="user-info"><p><strong>Phone:</strong> ' + (data.user?.id?.split(':')[0] || 'Unknown') + '</p><p><strong>Name:</strong> ' + (data.user?.name || 'Unknown') + '</p></div>';
                stopwatchSection.style.display = 'none';
                infoSection.innerHTML = '<p>You can close this page</p>';
                statusEl.style.display = 'none';
                stopStopwatch();
            } else if (type === 'reconnecting') {
                // Reconnecting
                statusEl.textContent = 'Reconnecting... Attempt ' + (data.data?.attempt || '?');
                statusEl.className = 'connection-status reconnecting';
            }
        }
        
        function connectSSE() {
            eventSource = new EventSource('/qr/stream');
            
            eventSource.onopen = () => {
                console.log('SSE connection opened');
                document.getElementById('connection-status').textContent = 'Real-time connection active';
                document.getElementById('connection-status').className = 'connection-status';
                document.getElementById('connection-status').style.background = '#e8f5e9';
                document.getElementById('connection-status').style.color = '#2e7d32';
            };
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('SSE message:', data);
                    
                    if (data.type === 'init') {
                        // Initial state - update UI based on connection state
                        if (data.qrImage) {
                            updateQRState('qr', { qrImage: data.qrImage });
                            lastQRTime = data.qrTimestamp;
                            startStopwatch();
                        } else if (data.status) {
                            // Update status badge based on server state
                            const badge = document.getElementById('status-badge');
                            const statusEl = document.getElementById('connection-status');
                            
                            if (data.status.state === 'connected') {
                                badge.textContent = 'Connected';
                                badge.className = 'status-badge status-connected';
                                statusEl.style.display = 'none';
                            } else if (data.status.state === 'qr_ready') {
                                badge.textContent = 'Waiting for Scan';
                                badge.className = 'status-badge status-qr_ready';
                                statusEl.textContent = 'QR code ready - scan with your phone';
                            } else if (data.status.state === 'connecting') {
                                badge.textContent = 'Connecting...';
                                badge.className = 'status-badge status-qr_ready';
                                statusEl.textContent = 'Initializing WhatsApp connection...';
                            } else {
                                badge.textContent = data.status.state.charAt(0).toUpperCase() + data.status.state.slice(1);
                                statusEl.textContent = 'Waiting for connection...';
                            }
                        }
                    } else if (data.type === 'qr') {
                        updateQRState('qr', data);
                    } else if (data.type === 'connected') {
                        updateQRState('connected', data);
                    } else if (data.type === 'reconnecting') {
                        updateQRState('reconnecting', data);
                    } else if (data.type === 'logout') {
                        location.reload();
                    }
                } catch (e) {
                    console.error('Failed to parse SSE data:', e);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('SSE error:', error);
                document.getElementById('connection-status').textContent = 'Connection lost - retrying...';
                document.getElementById('connection-status').className = 'connection-status reconnecting';
                
                // Auto-reconnect after 3 seconds
                setTimeout(() => {
                    if (eventSource.readyState === EventSource.CLOSED) {
                        connectSSE();
                    }
                }, 3000);
            };
        }
        
        // Start SSE connection when page loads
        connectSSE();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (eventSource) {
                eventSource.close();
            }
            stopStopwatch();
        });
    </script>
</body>
</html>`;
    
    res.setHeader('Content-Type', 'text/html');
    res.send(html);
});

app.post('/send', async (req, res) => {
    try {
        const { to, message, phone } = req.body;
        const recipient = to || phone;
        
        if (!recipient) {
            return res.status(400).json({
                success: false,
                error: 'Recipient phone number is required (to or phone field)'
            });
        }
        
        if (!message) {
            return res.status(400).json({
                success: false,
                error: 'Message text is required'
            });
        }

        const result = await client.sendMessage(recipient, message);
        
        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('[ERROR] Failed to send message:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/send-media', async (req, res) => {
    try {
        const { to, phone, mediaUrl, caption, mimetype, fileName } = req.body;
        const recipient = to || phone;
        
        if (!recipient) {
            return res.status(400).json({
                success: false,
                error: 'Recipient phone number is required (to or phone field)'
            });
        }
        
        if (!mediaUrl) {
            return res.status(400).json({
                success: false,
                error: 'mediaUrl is required'
            });
        }

        const result = await client.sendMedia(recipient, mediaUrl, caption, {
            mimetype: mimetype,
            fileName: fileName
        });
        
        res.json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('[ERROR] Failed to send media:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/restart', async (req, res) => {
    try {
        await client.restart();
        
        res.json({
            success: true,
            message: 'Baileys client restarted successfully'
        });
    } catch (error) {
        console.error('[ERROR] Failed to restart:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.get('/health', (req, res) => {
    const status = client.getStatus();
    const isHealthy = ['connected', 'qr_ready'].includes(status.state);
    
    res.status(isHealthy ? 200 : 503).json({
        success: isHealthy,
        status: status.state,
        timestamp: new Date().toISOString()
    });
});

// SSE endpoint for real-time QR updates
app.get('/qr/stream', async (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    // Send initial status
    const status = client.getStatus();
    const qrData = client.getQRCode();
    
    // Generate QR image if available
    let initData = { type: 'init', status };
    if (qrData && qrData.qr && !qrData.isExpired) {
        try {
            const qrImage = await QRCode.toDataURL(qrData.qr, { width: 300, margin: 2 });
            initData.qrImage = qrImage;
            initData.qrTimestamp = qrData.timestamp;
        } catch (err) {
            console.error('[ERROR] Failed to generate init QR image:', err.message);
        }
    }
    
    res.write(`data: ${JSON.stringify(initData)}\n\n`);
    
    // Add client to broadcast list
    sseClients.add(res);
    
    // Remove client on disconnect
    req.on('close', () => {
        sseClients.delete(res);
    });
});

async function startServer() {
    try {
        console.log('[INFO] Starting Baileys WhatsApp server...');
        console.log('[INFO] Auth directory:', AUTH_DIR);
        
        await client.initialize();
        
        app.listen(PORT, 'localhost', () => {
            console.log(`[INFO] Baileys server running on http://localhost:${PORT}`);
            console.log(`[INFO] QR Code page: http://localhost:${PORT}/qr/page`);
            console.log(`[INFO] Status endpoint: http://localhost:${PORT}/status`);
        });
    } catch (error) {
        console.error('[FATAL] Failed to start server:', error.message);
        process.exit(1);
    }
}

process.on('SIGINT', async () => {
    console.log('[INFO] Shutting down...');
    await client.disconnect();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('[INFO] Shutting down...');
    await client.disconnect();
    process.exit(0);
});

process.on('uncaughtException', (error) => {
    console.error('[UNCAUGHT EXCEPTION]:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[UNHANDLED REJECTION]:', reason);
});

startServer();
