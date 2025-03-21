/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 11:24:25
 * @LastEditTime: 2025-03-21 21:22:31
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */

// 检查浏览器是否支持Web Serial API和Web NFC API
async function checkBrowserSupport() {
    // 检查是否为移动设备
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    
    if (isMobile) {
        // 移动设备检查Web NFC支持
        if (!('NDEFReader' in window)) {
            const errorMsg = '您的手机浏览器不支持Web NFC。请确保：\n' +
                '1. 使用Chrome或Edge浏览器\n' +
                '2. 系统已开启NFC功能\n' +
                '3. 使用HTTPS环境';
            alert(errorMsg);
            return false;
        }
        return true;
    }
    
    // 桌面设备检查Web Serial支持
    if (!navigator?.serial) {
        const errorMsg = '您的浏览器不支持Web Serial API。请确保：\n' +
            '1. 使用的是Chrome或Edge浏览器\n' +
            '2. 浏览器版本不低于89\n' +
            '3. 使用HTTPS或localhost环境\n' +
            '4. 已在chrome://flags中启用#enable-experimental-web-platform-features';
        alert(errorMsg);
        return false;
    }

    // 检查是否在安全上下文中运行
    if (!window.isSecureContext) {
        alert('Web Serial API需要在安全上下文(HTTPS或localhost)中运行');
        return false;
    }

    // 检查是否有必要的API方法
    const requiredMethods = ['requestPort', 'getPorts'];
    const missingMethods = requiredMethods.filter(method => !navigator.serial[method]);
    if (missingMethods.length > 0) {
        alert(`浏览器的Web Serial API不完整，缺少以下方法：${missingMethods.join(', ')}`);
        return false;
    }

    return true;
}

class NFCDevice {
    constructor() {
        // 添加移动设备判断
        this.isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        this.ndefReader = null;
        
        // 设备状态
        this.port = null;
        this.reader = null;
        this.writer = null;
        this.initialized = false;
        this.reading = false;
        this.lastDeviceCheck = 0;
        this.deviceCheckInterval = 2000; // 2秒检查一次

        // 缓存DOM元素
        this.elements = {
            connectButton: document.getElementById('connectButton'),
            disconnectButton: document.getElementById('disconnectButton'),
            readCardButton: document.getElementById('readCardButton'),
            writeCardButton: document.getElementById('writeCardButton'),
            clearLogButton: document.getElementById('clearLogButton'),
            connectionStatus: document.getElementById('connectionStatus'),
            portInfo: document.getElementById('portInfo'),
            cardId: document.getElementById('cardId'),
            cardType: document.getElementById('cardType'),
            cardData: document.getElementById('cardData'),
            writeData: document.getElementById('writeData'),
            logContainer: document.getElementById('logContainer')
        };

        // 检查DOM元素是否都存在
        const missingElements = Object.entries(this.elements)
            .filter(([key, element]) => !element)
            .map(([key]) => key);

        if (missingElements.length > 0) {
            console.error('找不到以下DOM元素:', missingElements);
            alert('页面缺少必要的DOM元素，请检查HTML结构');
            return;
        }

        // 初始化事件监听
        this.initEventListeners();

        // 如果是移动设备，页面加载完成后预请求NFC权限
        if (this.isMobile && 'NDEFReader' in window) {
            // 延迟一秒执行，确保页面完全加载
            setTimeout(() => {
                const reader = new NDEFReader();
                reader.scan().catch(error => {
                    console.log('NFC预授权请求:', error);
                });
            }, 1000);
        }
    }

    // 初始化事件监听器
    initEventListeners() {
        this.elements.connectButton.addEventListener('click', () => this.connect());
        this.elements.disconnectButton.addEventListener('click', () => this.disconnect());
        this.elements.readCardButton.addEventListener('click', () => this.startReadingCard());
        this.elements.writeCardButton.addEventListener('click', () => this.writeCardData());
        this.elements.clearLogButton.addEventListener('click', () => this.clearLog());
    }

    // 记录日志
    log(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        this.elements.logContainer.appendChild(entry);
        this.elements.logContainer.scrollTop = this.elements.logContainer.scrollHeight;
    }

    // 清空日志
    clearLog() {
        this.elements.logContainer.innerHTML = '';
    }

    // 更新UI状态
    updateUIState(connected = false) {
        this.elements.connectButton.disabled = connected;
        this.elements.disconnectButton.disabled = !connected;
        this.elements.readCardButton.disabled = !connected;
        this.elements.writeCardButton.disabled = !connected;
        this.elements.connectionStatus.value = connected ? '已连接' : '未连接';
    }

    // 连接设备
    async connect() {
        try {
            if (!await checkBrowserSupport()) {
                return;
            }

            if (this.isMobile) {
                await this.connectMobileNFC();
            } else {
                await this.connectSerialDevice();
            }
        } catch (error) {
            this.log(`连接失败: ${error.message}`, 'error');
            await this.disconnect();
        }
    }

    // 新增移动端NFC连接方法
    async connectMobileNFC() {
        try {
            // 先检查系统NFC是否开启
            if (!('NDEFReader' in window)) {
                this.log('设备不支持NFC功能，请确保：\n1. 使用Chrome浏览器\n2. 系统已开启NFC功能', 'error');
                return;
            }

            // 创建NDEFReader实例并主动请求权限
            this.ndefReader = new NDEFReader();
            
            // 使用 layui 显示提示框
            layer.msg('请在系统弹出的授权提示中允许访问NFC功能', {
                icon: 16,
                time: 0,
                shade: 0.3
            });

            try {
                // 主动触发权限请求
                await this.ndefReader.scan();
                // 关闭提示框
                layer.closeAll();
                
                this.log('NFC功能已启动，请将NFC标签靠近手机背面');
                this.initialized = true;
                this.updateUIState(true);
                
                // 监听NFC读取事件
                this.ndefReader.addEventListener("reading", event => {
                    this.handleNFCReading(event);
                });

                this.ndefReader.addEventListener("readingerror", () => {
                    this.log('读取NFC标签失败', 'error');
                });

            } catch (error) {
                // 关闭提示框
                layer.closeAll();
                
                if (error.name === 'NotAllowedError') {
                    layer.confirm('需要授权访问NFC功能，是否重新请求权限？', {
                        btn: ['重新请求', '手动设置', '取消'],
                        title: 'NFC权限未授权'
                    }, 
                    // 重新请求按钮
                    async () => {
                        try {
                            const reader = new NDEFReader();
                            await reader.scan();
                            this.connect(); // 重新尝试连接
                        } catch (e) {
                            console.error('重新请求权限失败:', e);
                        }
                    },
                    // 手动设置按钮
                    () => {
                        // 原有的设置指导代码...
                    });
                } else if (error.name === 'NotSupportedError') {
                    layer.alert('设备不支持NFC功能，请确保：<br>' +
                        '1. 手机NFC功能已开启<br>' +
                        '2. 使用Chrome浏览器<br>' +
                        '3. 系统版本支持NFC功能', {
                        title: '设备不支持',
                        icon: 2
                    });
                } else {
                    layer.alert(`NFC启动失败: ${error.message}`, {
                        title: '错误',
                        icon: 2
                    });
                }
                throw error;
            }
        } catch (error) {
            console.error('NFC连接错误:', error);
            this.log(`NFC连接失败: ${error.message}`, 'error');
            throw error;
        }
    }

    // 新增处理NFC读取事件的方法
    async handleNFCReading(event) {
        try {
            // 更新卡片ID
            const cardId = event.serialNumber;
            this.elements.cardId.value = cardId;
            this.log(`检测到NFC标签: ${cardId}`);

            // 更新卡片类型
            this.elements.cardType.value = 'NDEF';
            
            // 读取NDEF消息
            let cardData = '';
            for (const record of event.message.records) {
                if (record.recordType === "text") {
                    const textDecoder = new TextDecoder();
                    const text = textDecoder.decode(record.data);
                    cardData += text;
                } else if (record.recordType === "url") {
                    cardData += record.data;
                }
            }
            
            this.elements.cardData.value = cardData;
            this.log(`读取数据: ${cardData}`);
            
        } catch (error) {
            this.log(`处理NFC数据失败: ${error.message}`, 'error');
        }
    }

    // 修改断开连接方法以支持移动端
    async disconnect() {
        try {
            if (this.isMobile && this.ndefReader) {
                // 停止NFC扫描
                this.ndefReader = null;
            } else {
                this.reading = false;
                if (this.reader) {
                    await this.reader.cancel();
                    this.reader = null;
                }
                if (this.writer) {
                    this.writer.releaseLock();
                    this.writer = null;
                }
                if (this.port?.readable) {
                    await this.port.close();
                }
            }
            this.initialized = false;
            this.updateUIState(false);
            this.log('设备已断开连接');
        } catch (error) {
            this.log(`断开连接错误: ${error.message}`, 'error');
        }
    }

    // 初始化设备
    async initializeDevice() {
        try {
            // 发送唤醒指令
            const wakeupCmd = new Uint8Array([
                0x55, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0xFF, 0x03, 0xFD, 0xD4, 0x14, 0x01, 0x17, 0x00
            ]);

            const response = await this.sendCommand(wakeupCmd);
            return response && response.includes('d5');
        } catch (error) {
            this.log(`设备初始化失败: ${error.message}`, 'error');
            return false;
        }
    }

    // 发送命令并等待响应
    async sendCommand(command) {
        if (!this.port?.writable) {
            throw new Error('设备未连接');
        }

        try {
            // 确保之前的writer已释放
            if (this.writer) {
                this.writer.releaseLock();
                this.writer = null;
            }
            
            this.writer = this.port.writable.getWriter();
            await this.writer.write(command);
            this.writer.releaseLock();
            this.writer = null;
            
            this.log(`发送命令: ${Array.from(command).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);

            // 增加等待时间
            await new Promise(resolve => setTimeout(resolve, 300));
            this.log('等待响应');
            
            // 确保之前的reader已释放
            if (this.reader) {
                this.reader.releaseLock();
                this.reader = null;
            }
            
            this.reader = this.port.readable.getReader();
            const { value } = await this.reader.read();
            this.reader.releaseLock();
            this.reader = null;
            
            if (value) {
                const response = Array.from(value).map(b => b.toString(16).padStart(2, '0')).join('');
                this.log(`收到响应: ${response}`);
                return response;
            }
            
            this.log('未收到响应', 'warn');
            return null;
        } catch (error) {
            if (this.writer) {
                this.writer.releaseLock();
                this.writer = null;
            }
            if (this.reader) {
                this.reader.releaseLock();
                this.reader = null;
            }
            throw new Error(`命令执行失败: ${error.message}`);
        }
    }

    // 读取卡片ID
    async readCardId() {
        try {
            const cmd = new Uint8Array([0x00, 0x00, 0xFF, 0x04, 0xFC, 0xD4, 0x4A, 0x01, 0x00, 0xE1, 0x00]);
            const response = await this.sendCommand(cmd);
            
            if (response && response.includes('d54b')) {
                const cardInfo = response.substring(response.indexOf('d54b') + 4);
                if (cardInfo.length >= 8) {
                    return cardInfo.toUpperCase();
                }
            }
            return null;
        } catch (error) {
            this.log(`读取卡片ID失败: ${error.message}`, 'error');
            return null;
        }
    }

    // 读取卡片类型
    async readCardType() {
        try {
            const response = await this.readCardId();
            if (!response) return null;

            // 提取ATQA和SAK
            const atqa = response.substring(4, 8);
            const sak = response.substring(8, 10);

            if (atqa === '0044' && sak === '00') {
                return 'NTAG215';
            } else if (atqa === '0004' && sak === '08') {
                return 'MIFARE_CLASSIC_1K';
            }
            return '未知类型';
        } catch (error) {
            this.log(`读取卡片类型失败: ${error.message}`, 'error');
            return null;
        }
    }

    // 读取卡片数据
    async readCardData(block = 0) {
        try {
            // 发送读卡命令
            const readCmd = new Uint8Array([
                0x00, 0x00, 0xFF,         // 帧头
                0x05,                     // 长度
                0xFB,                     // 长度校验
                0xD4, 0x40,               // 命令标识 (InDataExchange)
                0x01,                     // 目标号
                0x30, block,              // 读取命令和块号
                0x00                      // 校验和
            ]);
            
            // 计算校验和
            let checksum = 0;
            for (let i = 5; i < readCmd.length - 1; i++) {
                checksum ^= readCmd[i];
            }
            readCmd[readCmd.length - 1] = checksum;
            
            const dataResponse = await this.sendCommand(readCmd);
            
            if (dataResponse && dataResponse.includes('d541')) {
                const dataStart = dataResponse.indexOf('d541') + 6;
                if (dataResponse.length >= dataStart + 32) {
                    const data = dataResponse.substring(dataStart, dataStart + 32).toUpperCase();
                    return data;
                }
            }
            
            return null;
        } catch (error) {
            this.log(`读取数据失败: ${error.message}`, 'error');
            return null;
        }
    }

    // 写入卡片数据
    async writeCardData() {
        try {
            const data = this.elements.writeData.value;
            if (!data) {
                this.log('请输入要写入的数据', 'warn');
                return;
            }

            if (this.isMobile) {
                await this.writeMobileNFC(data);
            } else {
                await this.writeSerialDevice(data);
            }
        } catch (error) {
            this.log(`写入数据失败: ${error.message}`, 'error');
        }
    }

    // 新增移动端NFC写入方法
    async writeMobileNFC(data) {
        try {
            const writer = new NDEFWriter();
            await writer.write({
                records: [{
                    recordType: "text",
                    data: data
                }]
            });
            this.log('数据写入成功');
        } catch (error) {
            if (error.name === 'NotAllowedError') {
                this.log('需要授权写入NFC标签', 'error');
            } else if (error.name === 'NotSupportedError') {
                this.log('设备不支持NFC写入功能', 'error');
            } else {
                throw error;
            }
        }
    }

    // 开始读取卡片
    async startReadingCard() {
        if (!this.initialized) {
            this.log('设备未初始化', 'error');
            return;
        }

        try {
            // 读取卡片ID
            const cardId = await this.readCardId();
            if (!cardId) {
                this.log('未检测到卡片', 'warn');
                this.elements.cardId.value = '无';
                this.elements.cardType.value = '未知';
                this.elements.cardData.value = '';
                return;
            }

            this.elements.cardId.value = cardId;
            this.log(`检测到卡片: ${cardId}`);

            // 读取卡片类型
            const cardType = await this.readCardType();
            this.elements.cardType.value = cardType || '未知';
            this.log(`卡片类型: ${cardType || '未知'}`);

            // 分页读取数据
            this.log('开始分页读取...');
            const allData = [];
            let foundEnd = false;

            // 从第4页开始读取，最多读到第129页
            for (let page = 4; page < 130; page++) {
                if (foundEnd) break;

                const pageData = await this.readCardData(page);
                if (!pageData) {
                    this.log(`页 ${page} 读取失败`);
                    break;
                }

                this.log(`页 ${page} 数据: ${pageData}`);

                // 检查是否包含结束标记FE
                if (pageData.includes('FE')) {
                    const fePos = pageData.indexOf('FE');
                    const trimmedData = pageData.substring(0, fePos + 2); // 包含FE
                    foundEnd = true;

                    // 计算需要的填充量
                    const totalLen = allData.join('').length + trimmedData.length;
                    const paddingNeeded = totalLen % 8 === 0 ? 0 : 8 - (totalLen % 8);
                    
                    if (paddingNeeded > 0) {
                        allData.push(trimmedData + '00'.repeat(paddingNeeded));
                    } else {
                        allData.push(trimmedData);
                    }
                    
                    this.log(`找到结束标记FE，补充${paddingNeeded}字节填充`);
                } else {
                    allData.push(pageData);
                }

                // 读取间隔
                await new Promise(resolve => setTimeout(resolve, 50));
            }

            if (allData.length > 0) {
                const completeData = allData.join('');
                this.elements.cardData.value = completeData;
                this.log(`读取完成，总数据: ${completeData}`);
            } else {
                this.elements.cardData.value = '';
                this.log('未读取到有效数据', 'warn');
            }

        } catch (error) {
            this.log(`读取卡片失败: ${error.message}`, 'error');
        }
    }
}

// 初始化代码
(async function() {
    try {
        // 检查浏览器支持
        if (await checkBrowserSupport()) {
            // 创建NFC设备实例
            window.nfcDevice = new NFCDevice();
        }
    } catch (error) {
        console.error('初始化NFC设备失败:', error);
        alert('初始化NFC设备失败: ' + error.message);
    }
})();