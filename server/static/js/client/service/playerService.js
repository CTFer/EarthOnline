class PlayerService {
    constructor(api, eventBus) {
        this.api = api;
        this.eventBus = eventBus;
        this.playerId = localStorage.getItem('playerId') || '1';
        this.playerData = null;
        
        // 订阅相关事件
        this.setupEventListeners();
        console.log('[PlayerService] Initialized with playerId:', this.playerId);
    }

    setupEventListeners() {
        // 监听任务完成事件，更新玩家经验值
        this.eventBus.on('task:completed', this.handleTaskComplete.bind(this));
        // 监听NFC识别事件，更新玩家ID
        this.eventBus.on('nfc:identity', this.handleIdentityUpdate.bind(this));
    }

    async loadPlayerInfo() {
        console.log('[PlayerService] Loading player info');
        try {
            if (!this.api) {
                throw new Error('API client not initialized');
            }

            const result = await this.api.getPlayerInfo(this.playerId);
            
            if (result.code === 0) {
                this.playerData = result.data;
                this.updatePlayerUI(result.data);
                this.eventBus.emit('player:loaded', result.data);
                return result.data;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            console.error('[PlayerService] Load player info failed:', error);
            this.showPlayerError();
            this.eventBus.emit('player:error', error);
            throw error;
        }
    }

    updatePlayerUI(playerData) {
        console.log('[PlayerService] Updating player UI');
        document.getElementById('playerName').textContent = playerData.player_name;
        document.getElementById('playerPoints').textContent = playerData.points;
        
        this.updateLevelAndExp(playerData);
        this.eventBus.emit('player:ui-updated', playerData);
    }

    updateLevelAndExp(playerData) {
        const levelElement = document.querySelector('.level');
        const expElement = document.querySelector('.exp');
        const expBarInner = document.querySelector('.exp-bar-inner');

        if (levelElement) {
            levelElement.textContent = `${playerData.level}/100`;
        }
        if (expElement) {
            expElement.textContent = `${playerData.experience}/99999`;
        }
        if (expBarInner) {
            const expPercentage = (playerData.experience / 99999) * 100;
            expBarInner.style.width = `${Math.min(100, expPercentage)}%`;
        }
    }

    showPlayerError() {
        console.log('[PlayerService] Showing player error state');
        document.getElementById('playerName').textContent = '加载失败';
        document.getElementById('playerPoints').textContent = '0';
        
        const levelElement = document.querySelector('.level');
        const expElement = document.querySelector('.exp');
        const expBarInner = document.querySelector('.exp-bar-inner');

        if (levelElement) levelElement.textContent = '0/100';
        if (expElement) expElement.textContent = '0/99999';
        if (expBarInner) expBarInner.style.width = '0%';
        
        this.eventBus.emit('player:error-ui-updated');
    }

    // 处理任务完成事件
    async handleTaskComplete(taskData) {
        console.log('[PlayerService] Handling task complete:', taskData);
        if (taskData.points) {
            await this.loadPlayerInfo(); // 重新加载玩家信息以更新经验值
        }
    }

    // 处理身份识别更新
    handleIdentityUpdate(data) {
        console.log('[PlayerService] Handling identity update:', data);
        if (data.player_id) {
            this.playerId = data.player_id;
            localStorage.setItem('playerId', data.player_id);
            this.loadPlayerInfo();
            this.eventBus.emit('player:identity-updated', data);
        }
    }

    // 获取当前玩家ID
    getPlayerId() {
        return this.playerId;
    }

    // 获取玩家数据
    getPlayerData() {
        return this.playerData;
    }

    // 检查玩家是否已初始化
    isInitialized() {
        return !!this.playerData;
    }
}

export default PlayerService; 