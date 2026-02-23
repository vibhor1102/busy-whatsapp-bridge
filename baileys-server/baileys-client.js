const {
    makeWASocket,
    DisconnectReason,
    useMultiFileAuthState,
    Browsers,
    fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');
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
        this.qrScanTimeout = null;
        this.lastQRReceived = null;
    }

    async initialize() {
        try {
            const { state, saveCreds } = await useMultiFileAuthState(this.authDir);
            this.saveCreds = saveCreds;
            
            // Fetch latest WhatsApp web version
            const { version, isLatest } = await fetchLatestBaileysVersion();
            this.logger.info({ version, isLatest }, 'Fetched latest Baileys version');
            
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

            this.setupEventHandlers();
            this.logger.info('Baileys client initialized');
        } catch (error) {
            this.logger.error({ error: error.message }, 'Failed to initialize Baileys client');
            throw error;
        }
    }

    setupEventHandlers() {
        this.socket.ev.on('connection.update', async (update) => {
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
                    
                    setTimeout(() => {
                        this.initialize();
                    }, delay);
                } else if (statusCode === DisconnectReason.loggedOut) {
                    this.logger.error('Device logged out. Session invalid. Please scan QR again.');
                    this.qrCode = null;
                    this.emit('logout');
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
                
                const user = this.socket.user;
                this.logger.info(
                    { jid: user?.id, name: user?.name },
                    'Connection established'
                );
                
                this.emit('connected', { jid: user?.id, name: user?.name });
            }
        });

        this.socket.ev.on('creds.update', () => {
            if (this.saveCreds) {
                this.saveCreds();
                this.logger.debug('Credentials updated and saved');
            }
        });

        this.socket.ev.on('messages.upsert', ({ messages, type }) => {
            if (type === 'notify') {
                messages.forEach(msg => {
                    if (!msg.key.fromMe) {
                        this.emit('message', msg);
                    }
                });
            }
        });
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
        const fileName = options.fileName || mediaUrl.split('/').pop() || 'document.pdf';

        try {
            const result = await this.socket.sendMessage(jid, {
                document: { url: mediaUrl },
                caption: caption || '',
                mimetype: mimetype,
                fileName: fileName
            });

            this.logger.info(
                { to: jid, messageId: result.key.id, mediaUrl },
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

    async disconnect() {
        this.isShuttingDown = true;
        
        if (this.socket) {
            try {
                await this.socket.end();
                this.logger.info('Disconnected from WhatsApp');
            } catch (error) {
                this.logger.error({ error: error.message }, 'Error during disconnect');
            }
        }
        
        this.connectionState = 'disconnected';
        this.qrCode = null;
    }

    async restart() {
        this.isShuttingDown = false;
        await this.disconnect();
        
        this.reconnectAttempts = 0;
        await this.initialize();
        
        this.logger.info('Baileys client restarted');
    }
}

module.exports = BaileysClient;
