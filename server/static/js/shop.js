/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-02 16:04:10
 * @LastEditTime: 2025-02-02 23:12:55
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
layui.use(['layer', 'laytpl'], function(){
    var layer = layui.layer;
    var laytpl = layui.laytpl;
    
    // 获取当前用户ID
    const currentPlayerId = localStorage.getItem('playerId');
    
    // 加载用户积分
    loadUserPoints();
    
    // 加载商品列表
    loadItems();
    
    // 绑定排序按钮事件
    bindSortButtons();



// 加载用户积分
async function loadUserPoints() {
    try {
        const response = await fetch(`/api/player/${currentPlayerId}`);
        const result = await response.json();
        console.log(result);    
        if (result.code === 0) {
            document.getElementById('userPoints').textContent = result.data.points;
        }
    } catch (error) {
        console.error('加载积分失败:', error);
    }
}

// 创建商品卡片元素
function createItemCard(item) {
    const card = document.createElement('div');
    card.className = 'shop-item-card';
    
    card.innerHTML = `
        <div class="item-image">
            <img src="${item.image_url}" alt="${item.name}" />
        </div>
        <div class="item-info">
            <h3 class="item-name">${item.name}</h3>
            <p class="item-desc">${item.description}</p>
            <div class="item-price">
                <span class="price-icon">
                    <i class="layui-icon layui-icon-diamond"></i>
                </span>
                <span class="price-number">${item.price}</span>
            </div>
            <div class="item-stock">库存: ${item.stock}</div>
            <button class="layui-btn layui-btn-normal" onclick="purchaseItem(${item.id})">购买</button>
        </div>
    `;
    
    return card;
}

// 加载商品列表
async function loadItems(sort = 'price', order = 'asc') {
    try {
        const response = await fetch(`/api/shop/items?sort=${sort}&order=${order}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const container = document.getElementById('shopItems');
            container.innerHTML = ''; // 清空现有内容
            
            result.data.forEach(item => {
                container.appendChild(createItemCard(item));
            });
        }
    } catch (error) {
        console.error('加载商品列表失败:', error);
        layer.msg('加载商品列表失败');
    }
}

// 购买商品
async function purchaseItem(itemId) {
    try {
        const confirmed = await new Promise(resolve => {
            layer.confirm('确定购买此商品？', {
                btn: ['确定', '取消']
            }, () => resolve(true), () => resolve(false));
        });
        
        if (!confirmed) return;
        
        const response = await fetch('/api/shop/purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                user_id: currentPlayerId,
                item_id: itemId,
                quantity: 1
            })
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            layer.msg('购买成功');
            // 重新加载积分和商品列表
            await Promise.all([
                loadUserPoints(),
                loadItems()
            ]);
        } else {
            layer.msg('购买失败：' + result.msg);
        }
    } catch (error) {
        console.error('购买失败:', error);
        layer.msg('购买失败');
    }
}

// 绑定排序按钮事件
function bindSortButtons() {
    document.querySelectorAll('.shop-filter button').forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除所有按钮的active类
            document.querySelectorAll('.shop-filter button').forEach(b => {
                b.classList.remove('layui-btn-normal');
                b.classList.add('layui-btn-primary');
            });
            
            // 添加当前按钮的active类
            this.classList.remove('layui-btn-primary');
            this.classList.add('layui-btn-normal');
            
            // 加载排序后的商品
            loadItems(this.dataset.sort, this.dataset.order);
        });
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载用户积分
    loadUserPoints();
    
    // 加载商品列表
    loadItems();
    
    // 绑定排序按钮事件
    bindSortButtons();
}); 
});