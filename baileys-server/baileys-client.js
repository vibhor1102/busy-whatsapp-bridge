const {
    makeWASocket,
    DisconnectReason,
    useMultiFileAuthState,
    Browsers,
    fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');
const fs = require('fs/promises');
const EventEmitter = require('events');

class BaileysClient extends EventEmitter {
    constructor(options = {}) {
        super();
        this.authDir = options.authDir || path.join(__dirname, 'auth', 'baileys_session');
        this.sessionDir = path.dirname(this.authDir);
        this.socket = null;
        this.connectionState = 'disconnected';
        this.qrCode = null;
        this.qrTimestamp = null;
        this.logger = pino({
            level: options.logLevel || 'debug',
            transport: {
                target: 'pino-pretty',
                options: {
                    colorize: true,
                    translateTime: 'SYS:standard',
                    ignore: 'pid,hostname'
                }
            }
        });
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.isShuttingDown = false;
        this.isInitializing = false;
        this.qrScanTimeout = null;
        this.lastQRReceived = null;
        this.lastRecoveryAttempt = 0;
        this.recoveryCooldownMs = 5000;
        this.recoveryTimer = null;
        this.isRestarting = false;
        this.reconnectTimer = null;
        this.socketGeneration = 0;
    }

    async initialize() {
        if (this.isInitializing) {
            this.logger.debug('Initialization already in progress, skipping duplicate call');
            return;
        }

        this.isInitializing = true;
        try {
            this.connectionState = 'connecting';
            this.logger.info('Starting Baileys initialization...');
            
            const { state, saveCreds } = await useMultiFileAuthState(this.authDir);
            this.saveCreds = saveCreds;
            
            // Fetch latest WhatsApp web version
            const { version, isLatest } = await fetchLatestBaileysVersion();
            this.logger.info({ version, isLatest }, 'Fetched latest Baileys version');

            // Ensure only one active socket exists before creating a new one.
            if (this.socket?.ws && typeof this.socket.ws.close === 'function') {
                try {
                    this.socket.ws.close();
                } catch (error) {
                    this.logger.debug({ error: error.message }, 'Failed to close previous socket');
                }
            }

            this.socket = makeWASocket({
                version,
                auth: state,
                printQRInTerminal: false,
                logger: pino({ level: 'silent' }),
                browser: Browsers.macOS('Busy Whatsapp Bridge'),
                connectTimeoutMs: 60000,
                keepAliveIntervalMs: 25000,
                markOnlineOnConnect: false,
                emitOwnEvents: false,
                defaultQueryTimeoutMs: 60000
            });

            this.socketGeneration += 1;
            this.setupEventHandlers(this.socketGeneration);
            this.logger.info('Baileys client initialized');
        } catch (error) {
            this.logger.error({ error: error.message }, 'Failed to initialize Baileys client');
            throw error;
        } finally {
            this.isInitializing = false;
        }
    }

    cancelReconnectTimer() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    scheduleReconnect(delay) {
        if (this.isShuttingDown || this.isRestarting) {
            return;
        }
        this.cancelReconnectTimer();
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            if (this.isShuttingDown || this.isRestarting || this.connectionState === 'connected') {
                return;
            }
            this.initialize().catch((error) => {
                this.logger.error({ error: error.message }, 'Reconnect initialize failed');
            });
        }, delay);
    }

    setupEventHandlers(generation) {
        this.socket.ev.on('connection.update', async (update) => {
            if (generation !== this.socketGeneration) {
                return;
            }
            const { connection, lastDisconnect, qr } = update;

            this.logger.debug({ connection, hasQR: !!qr, lastDisconnect }, 'Connection update received');

            if (qr) {
                this.qrCode = qr;
                this.qrTimestamp = Date.now();
                this.lastQRReceived = Date.now();
                this.connectionState = 'qr_ready';
                this.emit('qr', qr);
                this.logger.info('QR code generated/updated, ready for scanning');
                
                // Reset reconnect attempts when user is actively trying to connect
                this.reconnectAttempts = 0;
                
                // Clear any existing QR timeout
                if (this.qrScanTimeout) {
                    clearTimeout(this.qrScanTimeout);
                }
                
                // Set timeout to clear old QR after 90 seconds (WhatsApp QR expires ~60s)
                this.qrScanTimeout = setTimeout(() => {
                    if (this.connectionState === 'qr_ready' && 
                        Date.now() - this.lastQRReceived > 85000) {
                        this.logger.info('QR code expired, waiting for new one...');
                        // Don't clear qrCode here - Baileys should send a new one
                        // If Baileys doesn't send new QR, it will close connection
                    }
                }, 90000);
            }

            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const errorMessage = lastDisconnect?.error?.message || 'Unknown error';
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                
                // Don't clear QR code immediately - might just be a temporary disconnect
                // while waiting for new QR from Baileys
                const wasQRReady = this.connectionState === 'qr_ready';
                this.connectionState = 'disconnected';
                
                this.logger.warn(
                    { statusCode, errorMessage, shouldReconnect, wasQRReady },
                    'Connection closed'
                );

                if (this.isShuttingDown) {
                    this.logger.info('Shutdown in progress, not reconnecting');
                    return;
                }

                // Don't increment reconnect attempts if we were waiting for QR scan
                // (user just needs more time, not a failure)
                if (statusCode === DisconnectReason.connectionClosed && wasQRReady) {
                    this.logger.info('Connection closed while waiting for QR scan - will retry');
                    // Keep reconnectAttempts the same, this is normal
                } else if (statusCode !== DisconnectReason.loggedOut) {
                    // Only increment for actual connection failures
                    this.reconnectAttempts++;
                }

                if (shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
                    const delay = wasQRReady ? 2000 : this.reconnectDelay * Math.pow(2, Math.min(this.reconnectAttempts - 1, 4));
                    
                    this.logger.info(
                        { attempt: this.reconnectAttempts, maxAttempts: this.maxReconnectAttempts, delay },
                        'Attempting to reconnect'
                    );
                    
                    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });
                    this.scheduleReconnect(delay);
                } else if (statusCode === DisconnectReason.loggedOut) {
                    if (this.isRestarting || errorMessage === 'Intentional Logout') {
                        this.logger.info('Logged out during intentional restart/logout flow');
                        return;
                    }
                    this.logger.error('Device logged out. Session invalid. Resetting session and preparing fresh QR.');
                    this.qrCode = null;
                    this.connectionState = 'logged_out';
                    this.emit('logout');
                    this.scheduleSessionRecovery('logged_out');
                } else {
                    this.logger.error('Max reconnection attempts reached');
                    this.emit('max_reconnect_reached');
                }
            }

            if (connection === 'connecting') {
                this.connectionState = 'connecting';
                this.logger.info('Connecting to WhatsApp...');
            }

            if (connection === 'open') {
                this.connectionState = 'connected';
                this.qrCode = null;
                this.reconnectAttempts = 0;
                this.cancelSessionRecovery();
                this.cancelReconnectTimer();
                
                const user = this.socket.user;
                this.logger.info(
                    { jid: user?.id, name: user?.name },
                    'Connection established'
                );
                
                this.emit('connected', { jid: user?.id, name: user?.name });
            }
        });

        this.socket.ev.on('creds.update', () => {
            if (generation !== this.socketGeneration) {
                return;
            }
            if (this.saveCreds) {
                this.saveCreds();
                this.logger.debug('Credentials updated and saved');
            }
        });

        this.socket.ev.on('messages.upsert', ({ messages, type }) => {
            if (generation !== this.socketGeneration) {
                return;
            }
            if (type === 'notify') {
                messages.forEach(msg => {
                    if (!msg.key.fromMe) {
                        this.emit('message', msg);
                    }
                });
            }
        });

        this.socket.ev.on('messages.update', (updates) => {
            if (generation !== this.socketGeneration) {
                return;
            }
            if (!Array.isArray(updates)) {
                return;
            }
            for (const item of updates) {
                try {
                    const key = item?.key || {};
                    if (!key.id || !key.fromMe) {
                        continue;
                    }
                    const statusValue = Number(item?.update?.status);
                    const mappedStatus = this.mapMessageStatus(statusValue);
                    if (!mappedStatus) {
                        continue;
                    }
                    this.emit('delivery_update', {
                        messageId: key.id,
                        deliveryStatus: mappedStatus,
                        recipientWaid: key.remoteJid || null,
                        eventTime: Date.now(),
                        raw: item,
                    });
                } catch (error) {
                    this.logger.debug({ error: error.message }, 'Failed to map messages.update item');
                }
            }
        });
    }

    mapMessageStatus(statusValue) {
        if (!Number.isFinite(statusValue)) {
            return null;
        }
        // Baileys/WA status generally escalates numerically.
        // We keep a conservative mapping for lifecycle reporting.
        if (statusValue >= 4) return 'read';
        if (statusValue >= 3) return 'delivered';
        if (statusValue >= 2) return 'sent';
        if (statusValue >= 1) return 'accepted';
        return 'accepted';
    }

    getStatus() {
        const qrAge = this.qrTimestamp ? Date.now() - this.qrTimestamp : null;
        const qrExpired = qrAge && qrAge > 60000;
        
        return {
            state: this.connectionState,
            qrAvailable: !!this.qrCode && !qrExpired,
            qrTimestamp: this.qrTimestamp,
            qrAge: qrAge,
            qrExpired: qrExpired,
            user: this.socket?.user || null,
            reconnectAttempts: this.reconnectAttempts
        };
    }

    async clearAuthState() {
        try {
            await fs.rm(this.authDir, { recursive: true, force: true });
            await fs.mkdir(this.authDir, { recursive: true });
            this.logger.info({ authDir: this.authDir }, 'Cleared stale auth state');
        } catch (error) {
            this.logger.warn({ error: error.message }, 'Failed to clear auth state');
        }
    }

    cancelSessionRecovery() {
        if (this.recoveryTimer) {
            clearTimeout(this.recoveryTimer);
            this.recoveryTimer = null;
        }
    }

    scheduleSessionRecovery(reason = 'unknown') {
        if (this.isShuttingDown) {
            return;
        }
        const now = Date.now();
        if (now - this.lastRecoveryAttempt < this.recoveryCooldownMs) {
            this.logger.debug({ reason }, 'Session recovery throttled');
            return;
        }

        this.lastRecoveryAttempt = now;
        this.cancelSessionRecovery();
        this.emit('reconnecting', { attempt: this.reconnectAttempts + 1, delay: 1500, reason });

        this.recoveryTimer = setTimeout(async () => {
            this.recoveryTimer = null;
            if (this.isShuttingDown || this.isInitializing || this.isRestarting) {
                return;
            }
            if (!['logged_out', 'disconnected'].includes(this.connectionState)) {
                this.logger.info({ state: this.connectionState }, 'Skipping session recovery because state changed');
                return;
            }
            try {
                await this.clearAuthState();
                await this.initialize();
            } catch (error) {
                this.logger.error({ error: error.message }, 'Session recovery failed');
            }
        }, 1500);
    }

    async ensureQrAvailable() {
        if (this.connectionState === 'connected') {
            return { state: this.connectionState, qrAvailable: false };
        }

        const qr = this.getQRCode();
        if (qr && !qr.isExpired) {
            return { state: this.connectionState, qrAvailable: true };
        }

        if (this.connectionState === 'logged_out' || this.connectionState === 'disconnected') {
            this.scheduleSessionRecovery('qr_requested');
        } else if (!this.isInitializing && this.connectionState !== 'connecting') {
            // Defensive re-init for unexpected stale states.
            this.logger.info({ state: this.connectionState }, 'No QR available; reinitializing');
            this.initialize().catch((error) => {
                this.logger.error({ error: error.message }, 'Failed to reinitialize while ensuring QR');
            });
        }

        return { state: this.connectionState, qrAvailable: false };
    }

    getQRCode() {
        if (!this.qrCode) {
            return null;
        }
        
        const age = Date.now() - this.qrTimestamp;
        const expiresIn = Math.max(0, 60000 - age);
        
        return {
            qr: this.qrCode,
            timestamp: this.qrTimestamp,
            expiresIn: expiresIn,
            age: age,
            isExpired: age > 60000
        };
    }

    async sendMessage(to, text, options = {}) {
        if (!this.socket || this.connectionState !== 'connected') {
            throw new Error('Not connected to WhatsApp');
        }

        let jid = this.formatPhoneNumber(to);

        try {
            const messageContent = options.mediaUrl
                ? {
                    document: { url: options.mediaUrl },
                    caption: text,
                    mimetype: 'application/pdf',
                    fileName: options.fileName || 'document.pdf'
                }
                : { text };

            const result = await this.socket.sendMessage(jid, messageContent);
            
            this.logger.info(
                { to: jid, messageId: result.key.id },
                'Message sent successfully'
            );

            return {
                success: true,
                messageId: result.key.id,
                timestamp: result.messageTimestamp
            };
        } catch (error) {
            this.logger.error(
                { to: jid, error: error.message },
                'Failed to send message'
            );
            throw error;
        }
    }

    async sendMedia(to, mediaUrl, caption, options = {}) {
        if (!this.socket || this.connectionState !== 'connected') {
            throw new Error('Not connected to WhatsApp');
        }

        let jid = this.formatPhoneNumber(to);
        const mimetype = options.mimetype || 'application/pdf';
        
        // Handle both URLs and local file paths
        let mediaSource;
        let fileName = options.fileName;
        
        // Check if it's a URL (http/https) or local file path
        if (mediaUrl.match(/^https?:\/\//i)) {
            // It's a URL
            mediaSource = { url: mediaUrl };
            fileName = fileName || mediaUrl.split('/').pop() || 'document.pdf';
        } else {
            // It's a local file path - convert to file:// URL for Baileys
            const path = require('path');
            const resolvedPath = path.resolve(mediaUrl);
            mediaSource = { url: resolvedPath };
            fileName = fileName || path.basename(resolvedPath) || 'document.pdf';
        }

        try {
            const result = await this.socket.sendMessage(jid, {
                document: mediaSource,
                caption: caption || '',
                mimetype: mimetype,
                fileName: fileName
            });

            this.logger.info(
                { to: jid, messageId: result.key.id, mediaUrl, isLocalFile: !mediaUrl.match(/^https?:\/\//i) },
                'Media message sent successfully'
            );

            return {
                success: true,
                messageId: result.key.id,
                timestamp: result.messageTimestamp
            };
        } catch (error) {
            this.logger.error(
                { to: jid, error: error.message, mediaUrl },
                'Failed to send media message'
            );
            throw error;
        }
    }

    formatPhoneNumber(phone) {
        let cleaned = phone.replace(/[^0-9]/g, '');
        
        if (!cleaned.startsWith('91') && cleaned.length === 10) {
            cleaned = '91' + cleaned;
        }
        
        return cleaned + '@s.whatsapp.net';
    }

    async setPresence(online = true) {
        /*
         * Set user presence (online/offline).
         * @param {boolean} online - true for 'available', false for 'unavailable'
         */
        if (!this.socket || this.connectionState !== 'connected') {
            this.logger.debug('Cannot set presence: not connected');
            return false;
        }

        try {
            const presence = online ? 'available' : 'unavailable';
            await this.socket.sendPresenceUpdate(presence);
            this.logger.debug({ presence }, 'Presence updated');
            return true;
        } catch (error) {
            this.logger.error({ error: error.message }, 'Failed to set presence');
            return false;
        }
    }

    async sendTypingIndicator(to, duration = 5000) {
        /*
         * Send typing indicator to a chat.
        
        Args:
         * @param {string} to - Phone number or JID
         * @param {number} duration - Duration in milliseconds to show typing
         * @returns {boolean} success
         */
        if (!this.socket || this.connectionState !== 'connected') {
            this.logger.debug('Cannot send typing: not connected');
            return false;
        }

        let jid = this.formatPhoneNumber(to);

        try {
            // Send typing state
            await this.socket.sendPresenceUpdate('composing', jid);
            this.logger.debug({ to: jid, duration }, 'Typing indicator sent');
            
            // Wait for the specified duration
            await new Promise(resolve => setTimeout(resolve, duration));
            
            // Clear typing state (set to available)
            await this.socket.sendPresenceUpdate('available', jid);
            
            return true;
        } catch (error) {
            this.logger.error({ to: jid, error: error.message }, 'Failed to send typing indicator');
            return false;
        }
    }

    async disconnect(forRestart = false) {
        this.isShuttingDown = !forRestart;
        this.isRestarting = forRestart;
        this.cancelSessionRecovery();
        this.cancelReconnectTimer();
        
        if (this.socket) {
            try {
                if (!forRestart && typeof this.socket.logout === 'function') {
                    await this.socket.logout();
                }
                if (this.socket.ws && typeof this.socket.ws.close === 'function') {
                    this.socket.ws.close();
                }
                this.logger.info('Disconnected from WhatsApp');
            } catch (error) {
                this.logger.error({ error: error.message }, 'Error during disconnect');
            } finally {
                this.socket = null;
            }
        }
        
        this.connectionState = 'disconnected';
        this.qrCode = null;
    }

    async restart() {
        try {
            await this.disconnect(true);
            this.reconnectAttempts = 0;
            this.isShuttingDown = false;
            this.connectionState = 'disconnected';
            await this.initialize();
            this.logger.info('Baileys client restarted');
        } finally {
            this.isRestarting = false;
        }
    }
}

module.exports = BaileysClient;
