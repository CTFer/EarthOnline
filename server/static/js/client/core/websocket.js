class WebSocketManager {
    constructor(url, eventBus) {
        this.url = url;
        this.eventBus = eventBus;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        console.log('[WebSocket] Initializing');
    }

    connect() {
        try {
            this.socket = io(this.url);
            this.setupEventHandlers();
            console.log('[WebSocket] Connected');
        } catch (error) {
            console.error('[WebSocket] Connection failed:', error);
            this.handleReconnect();
        }
    }

    setupEventHandlers() {
        // 任务相关
        this.socket.on('task_update', (data) => {
            console.log('[WebSocket] Task update received:', data);
            this.eventBus.emit('task:update', data);
        });

        // NFC相关
        this.socket.on('nfc_update', (data) => {
            console.log('[WebSocket] NFC update received:', data);
            this.eventBus.emit('nfc:update', data);
        });

        // 玩家相关
        this.socket.on('player_update', (data) => {
            console.log('[WebSocket] Player update received:', data);
            this.eventBus.emit('player:update', data);
        });

        // 连接状态
        this.socket.on('connect', () => {
            console.log('[WebSocket] Connected');
            this.eventBus.emit('ws:connected');
        });

        this.socket.on('disconnect', () => {
            console.log('[WebSocket] Disconnected');
            this.eventBus.emit('ws:disconnected');
            this.handleReconnect();
        });
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[WebSocket] Reconnecting... Attempt ${this.reconnectAttempts}`);
            setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
        }
    }

    // 发送消息方法
    emit(event, data) {
        if (this.socket && this.socket.connected) {
            console.log(`[WebSocket] Emitting ${event}:`, data);
            this.socket.emit(event, data);
        } else {
            console.error('[WebSocket] Cannot emit: socket not connected');
        }
    }
}

export default WebSocketManager; 