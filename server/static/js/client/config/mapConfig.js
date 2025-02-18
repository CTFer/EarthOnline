/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-16 19:30:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 地图配置文件
 */

// 默认渲染器类型
export const RENDER_TYPE = 'AMAP';  // 'AMAP' | 'ECHARTS'

// 高德地图配置
export const AMAP_CONFIG = {
    // 地图基础配置
    zoom: 12,                     // 默认缩放级别
    resizeEnable: true,          // 是否监控地图容器尺寸变化
    rotateEnable: false,         // 是否允许旋转
    showIndoorMap: false,        // 是否在有矢量底图的时候自动展示室内地图
    showBuildingBlock: false,     // 是否显示3D楼块
    viewMode: '2D',              // 地图视图模式
    features: ['bg', 'road'],    // 地图显示要素
    mapStyle: 'amap://styles/dark',  // 地图样式
    pitch: 0,                    // 俯仰角度

    // 卫星图层配置
    satellite: {
        visible: true,           // 是否默认显示卫星图层
        opacity: 1,              // 卫星图层透明度
        zIndex: 4,               // 图层叠加顺序
    },
    roadNet: {
        visible: false,           // 是否默认显示路网图层
        opacity: 1,              // 路网图层透明度
        zIndex: 5,               // 图层叠加顺序
    },

    // 安全配置
    securityJsCode: 'a64ba8d506a1154e41b9ca50a6113c55',  // 安全密钥
    key: '16de1da59d44d6967f9a6bf5248963c5',            // API密钥
};

// Echarts地图配置
export const ECHARTS_CONFIG = {
    // 地图基础样式
    backgroundColor: 'transparent',
    geo: {
        roam: true,              // 是否开启鼠标缩放和平移漫游
        label: {
            show: true,
            color: '#8aa2c1',
            fontSize: 10
        },
        itemStyle: {
            areaColor: '#15273f',
            borderColor: '#1e3148',
            borderWidth: 1
        },
        emphasis: {
            itemStyle: {
                areaColor: '#2a4a7c'
            }
        }
    }
};

// 点位样式配置
export const MARKER_STYLE = {
    point: {
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
            color: '#ffc447',
            borderColor: '#fff',
            borderWidth: 1
        },
        label: {
            show: true,
            position: 'top',
            color: '#fff',
            fontSize: 10
        }
    },
    start: {
        symbol: 'pin',
        symbolSize: 12,
        itemStyle: {
            color: '#4CAF50',
            borderColor: '#fff',
            borderWidth: 2
        }
    },
    end: {
        symbol: 'pin',
        symbolSize: 12,
        itemStyle: {
            color: '#F44336',
            borderColor: '#fff',
            borderWidth: 2
        }
    }
};

// 路径样式配置
export const PATH_STYLE = {
    lineStyle: {
        color: '#ffc447',
        width: 3,
        opacity: 0.8,
        type: 'solid',
        join: 'round',
        cap: 'round'
    },
    effect: {
        show: true,
        period: 6,
        trailLength: 0.7,
        color: '#fff',
        symbolSize: 3
    }
};

// 时间范围配置
export const TIME_RANGE_CONFIG = {
    default: 'today',
    options: [
        { value: 'today', label: '当日' },
        { value: 'week', label: '近一周' },
        { value: 'month', label: '近一月' },
        { value: 'year', label: '近一年' },
        { value: 'custom', label: '自定义时间范围' }
    ]
};

export default {
    RENDER_TYPE,
    AMAP_CONFIG,
    ECHARTS_CONFIG,
    MARKER_STYLE,
    PATH_STYLE,
    TIME_RANGE_CONFIG
}; 