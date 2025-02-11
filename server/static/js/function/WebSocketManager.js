// 新建 WebSocketManager 类
class WebSocketManager {
    constructor() {
        console.log('[WebSocket] 初始化 WebSocketManager');
        this.socket = io(SERVER);
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.taskUpdateCallback = null;
        this.tagsUpdateCallback = null;
        this.gpsUpdateCallback = null;
        this.nfcTaskUpdateCallback = null;  // 添加NFC任务更新回调
        this.initializeSocket();
    }

    initializeSocket() {
        console.log('[WebSocket] 开始初始化Socket连接');
        this.socket.on('connect', () => {
            console.log('[WebSocket] Connected to server');
            this.updateStatus(true, 'WebSocket已连接');
        });

        this.socket.on('disconnect', () => {
            console.log('[WebSocket] Disconnected from server');
            this.updateStatus(false, 'WebSocket已断开');
        });

        this.socket.on('connect_error', (error) => {
            console.error('[WebSocket] Connection error:', error);
            this.updateStatus(false, 'WebSocket连接错误');
        });

        // 添加 GPS 更新事件监听
        this.socket.on('gps_update', (data) => {
            console.log('[WebSocket] Received GPS update:', data);
            if (this.gpsUpdateCallback) {
                this.gpsUpdateCallback(data);
            }
        });

        // 添加NFC任务更新事件监听
        this.socket.on('nfc_task_update', (data) => {
            console.log('[WebSocket] 收到NFC任务更新:', data);
            if (this.nfcTaskUpdateCallback) {
                this.nfcTaskUpdateCallback(data);
            }
        });

        // 添加任务更新事件监听
        this.socket.on('task_update', (data) => {
            console.log('[WebSocket] 收到任务更新:', data);
            if (this.taskUpdateCallback) {
                this.taskUpdateCallback(data);
            }
        });
    }

    updateStatus(connected, message) {
        if (connected) {
            this.statusDot.classList.add('connected');
        } else {
            this.statusDot.classList.remove('connected');
        }
        this.statusText.textContent = message;
    }

    subscribeToTasks(playerId) {
        const room = `user_${playerId}`;
        this.socket.emit('subscribe_tasks', { 
            player_id: playerId,
            room: room 
        });
        this.socket.emit('join', { room: room });
    }

    onTaskUpdate(callback) {
        this.taskUpdateCallback = callback;
    }

    onTagsUpdate(callback) {
        this.tagsUpdateCallback = callback;
    }

    // 添加 GPS 更新回调注册方法
    onGPSUpdate(callback) {
        this.gpsUpdateCallback = callback;
    }

    // 订阅 GPS 更新
    subscribeToGPS(playerId) {
        const room = `user_${playerId}`;
        console.log('[WebSocket] Subscribing to GPS updates for room:', room);
        this.socket.emit('subscribe_gps', { player_id: playerId, room: room });
    }

    // 添加NFC任务更新回调注册方法
    onNFCTaskUpdate(callback) {
        console.log('[WebSocket] 注册NFC任务更新回调');
        this.nfcTaskUpdateCallback = callback;
    }
} 
export default WebSocketManager; 