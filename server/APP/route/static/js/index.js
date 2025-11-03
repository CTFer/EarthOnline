var laydate = layui.laydate;
var $ = layui.$;
var form = layui.form;
var routes = [];

// 页面加载完成后执行
$(document).ready(function() {
    // 添加header展开/收起功能
    $('.header .title').on('click', function() {
        $('.header').toggleClass('collapsed');
        setTimeout(function() {
          if(myChart) {
            myChart.resize();
          }
        }, 300); // 等待过渡动画完成后再调整大小
    });
});

// 日期
laydate.render({
  elem: "#date",
  fullPanel: true,
  type: "datetime",
});
// 声明全局城市列表变量，用于后续查找省份信息
var cityList = [];
// 声明城市-省份映射表，用于快速查找
var cityProvinceMap = {};
// 初始化points数组用于城市点显示
var points = [];

// 获取城市列表数据并建立城市-省份映射表
$.ajax({
  url: "/route/getCityList",
  data: "",
  async: true,
  dataType: "json",
  success: function (array) {
    console.log('[DEBUG] 获取到城市列表数据:', array.length, '条记录');
    
    // 存储完整的城市列表（包含省份信息）
    cityList = array;
    
    // 构建城市到省份的映射表，用于快速查找
    for (let index = 0; index < array.length; index++) {
      const element = array[index];
      // 兼容新旧格式
      if (Array.isArray(element)) {
        // 旧格式: [name, province]
        cityProvinceMap[element[0]] = element[1] || '';
        console.log('[DEBUG] 映射(旧格式): ' + element[0] + ' -> ' + (element[1] || ''));
      } else {
        // 新格式: {name, province, x, y}
        cityProvinceMap[element.name] = element.province || '';

      }
    }
    
    console.log('[DEBUG] 城市-省份映射表构建完成，共映射:', Object.keys(cityProvinceMap).length, '个城市');
    
    // 渲染城市下拉列表
    cities = '<option value="">直接选择或搜索选择</option>';
    for (let index = 0; index < array.length; index++) {
      const element = array[index];
      // 根据数据格式获取城市名称
      const cityName = Array.isArray(element) ? element[0] : element.name;
      cities += '<option value="' + cityName + '">' + cityName + "</option>";
    }
    $(".start").html(cities);
    $(".end").html(cities);
    form.render($("#route-form"));
  },
  error: function(xhr, status, error) {
    console.error('获取城市列表失败:', error);
  }
});
var uploadedDataURL = "/route/static/js/china.json";
var myChart = echarts.init(document.getElementById("map"));
myChart.showLoading();
var option = {
  backgroundColor: "transparent",
  // 地图属性配置
  geo: {
    map: "china",
    aspectScale: 0.8, //长宽比
    zoom: 1.2,
    roam: true,
    label: {
      //设置字体样式
      show: true, //字体是否显示
      fontSize: 14, //设置字体大小
      color: "#d0d0d0", //修改为浅灰色字体，提高与背景的区分度
    },
    itemStyle: {
      normal: {
        borderColor: "rgba(255,209,163, .5)",
        borderWidth: 1,
        areaColor: "rgba(73,86,166,.1)",
        shadowBlur: 5,
        shadowColor: "rgba(107,91,237,.7)",
      },
      emphasis: {
        borderColor: "#b0b0b0", //弱化边框颜色
        areaColor: "rgba(80,80,180,.2)", //弱化高亮颜色，降低透明度和饱和度
        borderWidth: 0.5,
        shadowBlur: 3, //减小阴影效果
        shadowColor: "rgba(100,100,200,.4)", //弱化阴影颜色
        borderWidth: 1,
        label: {
          show: true,
          color: "#ffffff" //高亮时文字保持白色，增加对比度
        },
      },
    },
    // 初始化regions数组，为后续的省份高亮做准备
    regions: []
  },
  series: [
    {
      type: "effectScatter",
      coordinateSystem: "geo", //该系列使用的坐标系
      showEffectOn: "render",
      zlevel: 1,
      rippleEffect: {
        //特效相关配置
        period: 15,
        scale: 4,
        brushType: "fill",
      },
      hoverAnimation: true,
      label: {
        normal: {
          formatter: "{b}",
          position: "right",
          offset: [1, 0],
          color: "#b0b0b0", //弱化城市文字颜色
          show: true,
        },
      },
      itemStyle: {
        normal: {
          color: "#68a0b8", //弱化城市点颜色，使用更柔和的蓝色
          shadowBlur: 5, //减小阴影效果
          shadowColor: "rgba(50,50,50,0.5)", //弱化阴影颜色
        },
      },
      symbolSize: 5,
      data: points,
    }, //地图线的动画效果
    // 飞机 series 1
    {
      type: "lines",
      zlevel: 2,
      effect: {
        show: true,
        period: 8, //箭头指向速度，值越小速度越快
        constantSpeed: 30,
        trailLength: 0.2, //特效尾迹长度[0,1]值越大，尾迹越长重
        // 飞机
        symbol:
          "path://M599.06048 831.309824l12.106752-193.404928 372.860928 184.430592L984.02816 710.206464 617.906176 367.33952 617.906176 151.638016c0-56.974336-46.188544-143.064064-103.158784-143.064064-56.974336 0-103.158784 86.089728-103.158784 143.064064L411.588608 367.33952 45.461504 710.206464l0 112.129024 366.660608-184.430592 14.999552 209.27488c0 5.05344 0.594944 9.892864 1.124352 14.749696l-66.591744 60.348416 0 66.587648 153.986048-50.879488 2.43712-0.80896 147.439616 51.688448 0-66.587648-68.758528-62.253056L599.06048 831.309824z ", //箭头图标
        symbolSize: 12, //图标大小
      },
      lineStyle: {
        normal: {
          color: new echarts.graphic.LinearGradient(
            0,
            0,
            0,
            1,
            [
              {
                offset: 0,
                color: "#58B3CC",
              },
              {
                offset: 1,
                color: "#F58158",
              },
            ],
            false
          ),
          width: 1, //线条宽度
          opacity: 0.1, //尾迹线条透明度
          curveness: 0.1, //尾迹线条曲直度
        },
      },
      // 飞机轨迹数据
      data: [],
    },
    // 火车  series 2
    {
      type: "lines",
      polyline: true,
      zlevel: 2,
      effect: {
        show: true,
        period: 16, //箭头指向速度，值越小速度越快
        trailLength: 0.3, //特效尾迹长度[0,1]值越大，尾迹越长重
        // 火车
        symbol:
          "path://M304.244973 732.218161a43.350032 43.350032 0 0 0 59.606293-14.33441 43.350032 43.350032 0 0 0-14.341635-59.606294C257.549764 601.987441 202.654173 504.110294 202.654173 396.457715c0-169.115699 137.585776-306.701475 306.701475-306.701474 169.115699 0 306.701475 137.585776 306.701475 306.701474 0 104.610852-52.547463 200.999647-140.562478 257.845989a43.342807 43.342807 0 0 0-12.896635 59.931419 43.328357 43.328357 0 0 0 59.931419 12.896635c112.854583-72.878628 180.227757-196.491244 180.227757-330.674043 0-216.916334-176.477979-393.401538-393.401538-393.401538-216.916334 0-393.401538 176.477979-393.401538 393.401538-0.007225 138.069851 70.386002 263.589868 188.290863 335.760446z,M869.088662 935.363635H552.698455V300.73362a43.350032 43.350032 0 0 0-86.700064 0v634.630015H149.60096a43.350032 43.350032 0 0 0 0 86.700064h719.487702a43.350032 43.350032 0 0 0 0-86.700064z", //箭头图标
        symbolSize: 8, //图标大小
      },
      lineStyle: {
        normal: {
          color: "#fff",
          width: 1, //线条宽度
          opacity: 0.1, //尾迹线条透明度
          curveness: 0, //尾迹线条曲直度
          type: "dashed",
        },
      },
      // 火车轨迹数据
      data: [],
    },
    // 自驾  series 3
    {
      type: "lines",
      polyline: true,
      zlevel: 2,
      effect: {
        show: true,
        period: 16, //箭头指向速度，值越小速度越快
        trailLength: 0.3, //特效尾迹长度[0,1]值越大，尾迹越长重
        // 汽车
        symbol:"path://M201.4 349.4l9.8-9.2V330c0-11.3 9.2-20.5 20.5-20.5h18.9C263.9 307 439 271.1 515.3 288c74.8 16.9 193.5 94.7 205.3 102.4l126 33.8c39.9 10.8 63.5 46.1 63.5 94.2v62.5c0 19.5-15.9 35.3-35.3 35.3h-63.5c-3.1 0-5.6-2.6-5.6-5.6 0-3.1 2.6-5.6 5.6-5.6h63.5c13.3 0 24.1-10.8 24.1-24.1v-62.5c0-43-20.5-74.2-55.8-83.5l-127-34.3c-0.5 0-1 0-1.5-0.5-1-0.5-127-84-202.2-100.9-75.3-16.4-258.6 21.5-260.6 22h-20.5c-5.1 0-9.2 4.1-9.2 9.2v12.8c0 1.5-0.5 3.1-1.5 4.1l-12 11.1M183 382l-4.9 4.6-12 11.1c-1 1-2 1.5-3.6 1.5-12.8 0-23 10.2-23 23v62c0 3.1-2.6 5.6-5.6 5.6-5.1 0-9.2 4.1-9.2 9.2v81.9c0 13.3 10.8 24.1 24.1 24.1h44.5c3.1 0 5.6 2.6 5.6 5.6 0 3.1-2.6 5.6-5.6 5.6h-44.5c-19.5 0-35.3-15.9-34.8-34.8v-81.9c0-9.7 6.1-17.4 14.8-20v-57.3c0-18.4 13.8-33.3 31.7-34.3l11.4-10.7 4.6-4.3m-27.8 243.3,M116.3 612.5c-8.3-8.5-12.7-19.6-12.4-31.3v-81.8c0-11.1 5.7-21 14.8-26.4v-50.9c0-22.2 16.1-40.8 37.4-43.9l13.5-12.7c4-3.8 10.4-3.6 14.1 0.4 1.7 1.9 2.6 4.2 2.7 6.6 1.4 0.5 2.8 1.4 3.9 2.6 3.7 4.1 3.5 10.4-0.6 14.1l-16.8 15.5c-2.9 2.9-6.5 4.3-10.5 4.3-7.3 0-13 5.7-13 13v62c0 8.4-6.6 15.2-14.8 15.6v81.2c0 7.8 6.3 14.1 14.1 14.1h44.5c8.6 0 15.6 7 15.6 15.6s-7 15.6-15.6 15.6h-44.5c-12.1 0.1-23.9-4.9-32.4-13.6z m679.3-1.9c0-8.6 7-15.6 15.6-15.6h63.5c7.8 0 14.1-6.3 14.1-14.1v-62.5c0-38.9-17.6-65.8-48.4-73.8l-126.1-34.1c-2.2-0.3-4.1-1-5.7-2.3-0.3-0.2-0.7-0.5-1.2-0.8-30.2-19.4-133.6-84.1-197.3-98.4-73-15.9-253.4 21.4-256.2 22-0.7 0.2-1.5 0.3-2.3 0.3H232v12c0 4.3-1.6 8.3-4.5 11.2l-0.3 0.3-12 11.1c-4.1 3.7-10.4 3.5-14.1-0.6-1.6-1.8-2.5-4-2.6-6.3-1.6-0.5-3.1-1.4-4.3-2.7-3.8-4-3.6-10.4 0.4-14.1l6.6-6.2v-6c0-16.8 13.7-30.5 30.5-30.5h18c0.4-0.1 0.9-0.2 1.5-0.3 57.5-11.3 198.5-36 266.3-21 69.6 15.7 175 81.9 207.2 102.9l124.4 33.4c44.4 11.9 70.9 50.8 70.9 103.9v62.5c0 25-20.3 45.3-45.3 45.3h-63.5c-8.6 0-15.6-7-15.6-15.6z,M314.6 616.2c-3.1 0-5.6-2.6-5.6-5.6 0-3.1 2.6-5.6 5.6-5.6h374.8c3.1 0 5.6 2.6 5.6 5.6 0 3.1-2.6 5.6-5.6 5.6H314.6z m575.5-109.1,M299 610.6c0-8.6 7-15.6 15.6-15.6h374.8c8.6 0 15.6 7 15.6 15.6s-7 15.6-15.6 15.6H314.6c-8.6 0-15.6-7-15.6-15.6z m15.6 4.3z,M750.3 658.2c-38.9 0-70.7-31.7-70.7-70.7 0-38.9 31.7-70.7 70.7-70.7 38.9 0 70.7 31.7 70.7 70.7 0 38.9-31.7 70.7-70.7 70.7z m0-130.1c-32.8 0-59.4 26.6-59.4 59.4s26.6 59.4 59.4 59.4 59.4-26.6 59.4-59.4c0-32.7-26.6-59.4-59.4-59.4zM253.7 658.2c-38.9 0-70.7-31.7-70.7-70.7 0-38.9 31.7-70.7 70.7-70.7 38.9 0 70.7 31.7 70.7 70.7 0 38.9-31.8 70.7-70.7 70.7z m0-130.1c-32.8 0-59.4 26.6-59.4 59.4s26.6 59.4 59.4 59.4 59.4-26.6 59.4-59.4c0-32.7-26.6-59.4-59.4-59.4z m0 0,M173 587.5c0-44.5 36.2-80.7 80.7-80.7s80.7 36.2 80.7 80.7-36.2 80.7-80.7 80.7S173 632 173 587.5z m31.3 0c0 27.2 22.2 49.4 49.4 49.4s49.4-22.2 49.4-49.4-22.2-49.4-49.4-49.4-49.4 22.2-49.4 49.4z m465.4 0c0-44.5 36.2-80.7 80.7-80.7s80.7 36.2 80.7 80.7-36.2 80.7-80.7 80.7-80.7-36.2-80.7-80.7z m31.2 0c0 27.2 22.2 49.4 49.4 49.4s49.4-22.2 49.4-49.4-22.2-49.4-49.4-49.4-49.4 22.2-49.4 49.4z,M144.3 393.1h618.6v30H144.3z,M388.222 407.994l1.064-119.7 30 0.267-1.064 119.7z", //箭头图标
        symbolSize: 8, //图标大小
      },
      lineStyle: {
        normal: {
          color: "#fff",
          width: 2, //线条宽度
          opacity: 0.1, //尾迹线条透明度
          curveness: 0, //尾迹线条曲直度
          // type: "dashed",
        },
      },
      // 轨迹数据
      data: [],
    },
    // 汽车  series 4
    {
      type: "lines",
      polyline: true,
      zlevel: 2,
      effect: {
        show: true,
        period: 16, //箭头指向速度，值越小速度越快
        trailLength: 0.3, //特效尾迹长度[0,1]值越大，尾迹越长重
        // 大巴
        symbol:"path://M885.5 269H196.272c-16.898 0-32.556 7.639-42.957 20.959L59.543 410.055C52.1 419.588 48 431.5 48 443.595V590.5c0 30.052 24.448 54.5 54.5 54.5h50.626c2.613 52.275 45.962 94 98.874 94s96.261-41.725 98.874-94h311.251c2.613 52.275 45.962 94 98.874 94s96.261-41.725 98.874-94H885.5c30.052 0 54.5-24.448 54.5-54.5v-267c0-30.051-24.448-54.5-54.5-54.5zM252 709c-38.047 0-69-30.953-69-69s30.953-69 69-69 69 30.953 69 69-30.953 69-69 69z m509 0c-38.047 0-69-30.953-69-69s30.953-69 69-69 69 30.953 69 69-30.953 69-69 69z m149-118.5c0 13.51-10.99 24.5-24.5 24.5h-28.7c-11.105-42.524-49.844-74-95.8-74-45.955 0-84.695 31.476-95.8 74H347.8c-11.105-42.524-49.844-74-95.8-74s-84.695 31.476-95.8 74h-53.7C88.99 615 78 604.01 78 590.5V443.595a24.615 24.615 0 0 1 5.189-15.078l93.771-120.094c4.676-5.988 11.715-9.422 19.312-9.422H885.5c13.51 0 24.5 10.991 24.5 24.5V590.5z,M828 442h-60v-88c0-8.284-6.716-15-15-15s-15 6.716-15 15v88H595v-88c0-8.284-6.716-15-15-15s-15 6.716-15 15v88H423v-88c0-8.284-6.716-15-15-15s-15 6.716-15 15v88H249v-88c0-8.284-6.716-15-15-15s-15 6.716-15 15v88h-59c-8.284 0-15 6.716-15 15s6.716 15 15 15h668c8.284 0 15-6.716 15-15s-6.716-15-15-15z", //箭头图标
        symbolSize: 8, //图标大小
      },
      lineStyle: {
        normal: {
          color: "#fff",
          width: 2, //线条宽度
          opacity: 0.1, //尾迹线条透明度
          curveness: 0, //尾迹线条曲直度
          // type: "dashed",
        },
      },
      // 轨迹数据
      data: [],
    },
  ],
};

$.getJSON(uploadedDataURL, function (geoJson) {
  console.log('[DEBUG] 开始注册地图数据...');
  echarts.registerMap("china", geoJson);
  console.log('[DEBUG] 地图数据注册完成');
  myChart.hideLoading();
  
  // 确保series[0]配置正确用于显示城市点
  if (!option.series[0]) {
    console.error('[DEBUG] series[0]不存在，创建默认配置');
    option.series.unshift({
      type: "effectScatter",
      coordinateSystem: "geo",
      showEffectOn: "render",
      zlevel: 1,
      rippleEffect: {
        period: 15,
        scale: 4,
        brushType: "fill",
      },
      hoverAnimation: true,
      label: {
        normal: {
          formatter: "{b}",
          position: "right",
          offset: [1, 0],
          color: "#F58158",
          show: true,
        },
      },
      itemStyle: {
        normal: {
          color: "#46bee9",
          shadowBlur: 10,
          shadowColor: "#333",
        },
      },
      symbolSize: 5,
      data: points,
    });
  }
  
  // 设置城市点数据
  option.series[0].data = points;
  console.log('[DEBUG] 初始设置城市点数据:', points.length, '个点');

  myChart.setOption(option, true);
  
  // 确保地图在初始化后正确显示完整高度
  myChart.resize();
  console.log('[DEBUG] 地图初始化完成');
});

// 监听窗口大小变化，重新调整地图大小
window.addEventListener('resize', function() {
  if(myChart) {
    myChart.resize();
  }
});

// 改进的城市到省份映射函数
function getProvinceFromCity(cityName) {
  // 首先尝试从全局映射表中查找（从数据库加载）
  if (cityProvinceMap && cityProvinceMap[cityName]) {
    console.log('从映射表找到省份:', cityName, '->', cityProvinceMap[cityName]);
    return cityProvinceMap[cityName];
  }
  
  // 后备映射表，包含更多常见城市
  const fallbackMap = {
    // 直辖市
    '北京': '北京',
    '上海': '上海',
    '天津': '天津',
    '重庆': '重庆',
    // 特别行政区
    '香港': '香港',
    '澳门': '澳门',
    '台北': '台湾',
    // 省份映射
    '南京': '江苏省',
    '无锡': '江苏省',
    '徐州': '江苏省',
    '常州': '江苏省',
    '苏州': '江苏省',
    '杭州': '浙江省',
    '宁波': '浙江省',
    '温州': '浙江省',
    '嘉兴': '浙江省',
    '湖州': '浙江省',
    '广州': '广东省',
    '深圳': '广东省',
    '珠海': '广东省',
    '汕头': '广东省',
    '佛山': '广东省',
    '成都': '四川省',
    '绵阳': '四川省',
    '德阳': '四川省',
    '自贡': '四川省',
    '泸州': '四川省',
    '武汉': '湖北省',
    '黄石': '湖北省',
    '十堰': '湖北省',
    '宜昌': '湖北省',
    '襄阳': '湖北省',
    '西安': '陕西省',
    '铜川': '陕西省',
    '宝鸡': '陕西省',
    '咸阳': '陕西省',
    '渭南': '陕西省',
    '济南': '山东省',
    '青岛': '山东省',
    '淄博': '山东省',
    '枣庄': '山东省',
    '东营': '山东省',
    '沈阳': '辽宁省',
    '大连': '辽宁省',
    '鞍山': '辽宁省',
    '抚顺': '辽宁省',
    '本溪': '辽宁省',
    '哈尔滨': '黑龙江省',
    '齐齐哈尔': '黑龙江省',
    '鸡西': '黑龙江省',
    '鹤岗': '黑龙江省',
    '双鸭山': '黑龙江省',
    '石家庄': '河北省',
    '唐山': '河北省',
    '秦皇岛': '河北省',
    '邯郸': '河北省',
    '邢台': '河北省',
    '郑州': '河南省',
    '开封': '河南省',
    '洛阳': '河南省',
    '平顶山': '河南省',
    '安阳': '河南省',
    '长沙': '湖南省',
    '株洲': '湖南省',
    '湘潭': '湖南省',
    '衡阳': '湖南省',
    '邵阳': '湖南省',
    '福州': '福建省',
    '厦门': '福建省',
    '莆田': '福建省',
    '三明': '福建省',
    '泉州': '福建省',
    '南昌': '江西省',
    '景德镇': '江西省',
    '萍乡': '江西省',
    '九江': '江西省',
    '新余': '江西省',
    '合肥': '安徽省',
    '芜湖': '安徽省',
    '蚌埠': '安徽省',
    '淮南': '安徽省',
    '马鞍山': '安徽省',
    '昆明': '云南省',
    '曲靖': '云南省',
    '玉溪': '云南省',
    '保山': '云南省',
    '昭通': '云南省',
    '贵阳': '贵州省',
    '六盘水': '贵州省',
    '遵义': '贵州省',
    '安顺': '贵州省',
    '毕节': '贵州省',
    '南宁': '广西壮族自治区',
    '柳州': '广西壮族自治区',
    '桂林': '广西壮族自治区',
    '梧州': '广西壮族自治区',
    '北海': '广西壮族自治区',
    '海口': '海南省',
    '三亚': '海南省',
    '三沙': '海南省',
    '儋州': '海南省',
    '拉萨': '西藏自治区',
    '日喀则': '西藏自治区',
    '昌都': '西藏自治区',
    '林芝': '西藏自治区',
    '山南市': '西藏自治区',
    '乌鲁木齐': '新疆维吾尔自治区',
    '克拉玛依': '新疆维吾尔自治区',
    '吐鲁番': '新疆维吾尔自治区',
    '哈密': '新疆维吾尔自治区',
    '阿克苏': '新疆维吾尔自治区',
    '银川': '宁夏回族自治区',
    '石嘴山': '宁夏回族自治区',
    '吴忠': '宁夏回族自治区',
    '固原': '宁夏回族自治区',
    '中卫': '宁夏回族自治区',
    '西宁': '青海省',
    '海东': '青海省',
    '海北': '青海省',
    '黄南': '青海省',
    '海南州': '青海省',
    '兰州': '甘肃省',
    '嘉峪关': '甘肃省',
    '金昌': '甘肃省',
    '白银': '甘肃省',
    '天水': '甘肃省',
    '呼和浩特': '内蒙古自治区',
    '包头': '内蒙古自治区',
    '乌海': '内蒙古自治区',
    '赤峰': '内蒙古自治区',
    '通辽': '内蒙古自治区'
  };
  
  // 尝试直接查找
  if (fallbackMap[cityName]) {
    console.log('从后备映射表找到省份:', cityName, '->', fallbackMap[cityName]);
    return fallbackMap[cityName];
  }
  
  // 尝试模糊匹配
  for (let city in fallbackMap) {
    if (cityName.startsWith(city)) {
      console.log('模糊匹配到省份:', cityName, '->', fallbackMap[city]);
      return fallbackMap[city];
    }
  }
  
  // 尝试反向匹配，看省份是否包含在城市名中
  const provinces = [
    '北京', '上海', '天津', '重庆', '香港', '澳门', '台湾',
    '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
    '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆'
  ];
  
  for (let i = 0; i < provinces.length; i++) {
    if (cityName.includes(provinces[i])) {
      console.log('反向匹配到省份:', cityName, '->', provinces[i]);
      return provinces[i];
    }
  }
  
  console.log('未找到省份信息，返回城市名:', cityName);
  // 如果找不到匹配的省份，返回城市名作为后备
  return cityName;
}

// 已合并到上面的$(document).ready()函数中
$("#btn-add").on("click", function () {
  form.submit("route-form", function (data) {
    var field = data.field; // 获取表单全部字段值
    var start_date = new Date(field.date);
    field.date = start_date.getTime() / 1000;
    console.log(field); // 回调函数返回的 data 参数和提交事件中返回的一致
    // 执行提交
    addRoute(field);
    layer.msg(JSON.stringify(field), {
      title: "当前填写的字段值",
    });
  });
  return false;
});
$("#btn-exchange").on("click", function () {
  exchange();
  return false;
});
$("#btn-list").on("click", function () {
  showList();
  return false;
});

// 添加城市
  // 获取城市坐标
  console.log('[DEBUG] 开始获取城市数据...');
  $.ajax({
    url: "/route/getCity",
    data: "",
    async: true,
    dataType: "json",
    success: function (array) {
      console.log('[DEBUG] 成功获取城市数据:', array.length, '个城市');
      // 清除之前的城市数据
      window.points = [];
    
    // 确保provincesWithRecords已初始化
    if (!window.provincesWithRecords) {
      window.provincesWithRecords = new Set();
    }
    
    // 处理每个城市数据
    for (let index = 0; index < array.length; index++) {
      const element = array[index];
      let cityName, cityX, cityY, cityProvince;
      
      // 兼容新旧格式
      if (Array.isArray(element)) {
        // 旧格式: 数组 [name, x, y]
        cityName = element[0];
        cityX = element[1];
        cityY = element[2];
        // 尝试通过城市名获取省份
        cityProvince = getProvinceFromCity(cityName);
      } else {
        // 新格式: 对象 {name, x, y, province}
        cityName = element.name;
        cityX = element.x || element[1] || 0;
        cityY = element.y || element[2] || 0;
        cityProvince = element.province;
      }
      
      console.log('[DEBUG] 处理城市:', cityName, '坐标:', cityX, cityY, '省份:', cityProvince);
      
      // 创建城市点 - 确保格式完全正确
      window.points.push({ 
        name: cityName,
        value: [parseFloat(cityX), parseFloat(cityY)], // 确保是数字
        symbolSize: 8, // 增加点大小
        itemStyle: { 
          color: "#f34e2b",
          borderColor: '#fff',
          borderWidth: 1
        },
        label: { // 强制显示标签
          show: true,
          formatter: '{b}',
          position: 'right',
          color: '#f34e2b',
          fontSize: 12
        },
        province: cityProvince // 添加省份信息
      });
      
      // 如果城市有省份信息，也加入到有记录的省份集合中
      if (cityProvince) {
        window.provincesWithRecords.add(cityProvince);
      }
    }

    console.log('[DEBUG] 城市点数据准备完成:', window.points.length, '个点');
    
    // 如果存在更新地图函数，则调用它
    if (typeof updateMap === 'function') {
      updateMap(window.points, window.plane_route, window.train_route, window.drive_route, window.bus_route, window.provincesWithRecords);
    } else {
      // 如果updateMap不存在，则直接更新图表
      if (option && option.series && option.series[0]) {
        console.log('[DEBUG] 直接更新图表城市点数据');
        option.series[0].data = window.points;
        option.series[0].symbolSize = 8;
        option.series[0].label.show = true;
        myChart.setOption(option, true);
        myChart.resize();
      }
    }
  },
  error: function () {
    console.error('获取城市数据失败');
  }
});

let index = -1;
// 添加路径
var plane_route = [];
var train_route = [];
var drive_route = [];
var bus_route = [];
// 获取路径并高亮省份
$.ajax({
  url: "/route/getRoute",
  data: "",
  async: true,
  dataType: "json",
  success: function (array) {
    console.log('获取到路线数据:', array.length, '条记录');
    routes = array;
    
    // 用于存储有记录的省份及其访问次数
    const provincesWithRecords = new Map();
    
    // 清除之前的路径数据
    plane_route = [];
    train_route = [];
    drive_route = [];
    bus_route = [];
    
    // 从起点和终点城市获取省份信息
    for (let index = 0; index < array.length; index++) {
      const element = array[index];
      
      // 从起点城市获取省份信息并统计访问次数
      if (element.start && element.start_province) { 
        // 增加起点省份的访问次数
        const currentCount = provincesWithRecords.get(element.start_province) || 0;
        provincesWithRecords.set(element.start_province, currentCount + 1);
        console.log('起点省份访问记录更新:', element.start_province, '->', currentCount + 1);
      } else if (element.start) {
        // 如果API没有返回省份信息，使用后备函数
        const province = getProvinceFromCity(element.start);
        console.log('起点城市省份映射(后备):', element.start, '->', province);
        // 增加起点省份的访问次数
        const currentCount = provincesWithRecords.get(province) || 0;
        provincesWithRecords.set(province, currentCount + 1);
        console.log('起点省份访问记录更新:', province, '->', currentCount + 1);
      }
      
      // 从终点城市获取省份信息并统计访问次数
      if (element.end && element.end_province) { 
        console.log('终点城市省份映射(直接从API获取):', element.end, '->', element.end_province);
        // 增加终点省份的访问次数
        const currentCount = provincesWithRecords.get(element.end_province) || 0;
        provincesWithRecords.set(element.end_province, currentCount + 1);
        console.log('终点省份访问记录更新:', element.end_province, '->', currentCount + 1);
      } else if (element.end) {
        // 如果API没有返回省份信息，使用后备函数
        const province = getProvinceFromCity(element.end);
        console.log('终点城市省份映射(后备):', element.end, '->', province);
        // 增加终点省份的访问次数
        const currentCount = provincesWithRecords.get(province) || 0;
        provincesWithRecords.set(province, currentCount + 1);
        console.log('终点省份访问记录更新:', province, '->', currentCount + 1);
      }
      
      // 飞机路径
      if (element.method == "plane") {
        plane_route.push({
          coords: [
            [element.start_x, element.start_y],
            [element.end_x, element.end_y],
          ],
          lineStyle: { 
            color: "#4ab2e5",
            width: 2, // 增加线条宽度使其更明显
            opacity: 0.8 // 增加不透明度
          },
        });
      }
      // 火车路径
      if (element.method == "train") {
        train_route.push({
          coords: [
            [element.start_x, element.start_y],
            [element.end_x, element.end_y],
          ],
          lineStyle: { 
            color: "#b9be23",
            width: 2,
            opacity: 0.8
          },
        });
      }
      // 自驾路径
      if (element.method == "drive") {
        drive_route.push({
          coords: [
            [element.start_x, element.start_y],
            [element.end_x, element.end_y],
          ],
          lineStyle: { 
            color: "#d4237a",
            width: 2,
            opacity: 0.8
          },
        });
      }
      // 公交路径
      if (element.method == "bus") {
        bus_route.push({
          coords: [
            [element.start_x, element.start_y],
            [element.end_x, element.end_y],
          ],
          lineStyle: { 
            color: "#1296db",
            width: 2,
            opacity: 0.8
          },
        });
      }
    }
    
    // 配置省份高亮
    const regions = [];
    
    // 获取所有省份的访问次数，找出最大值
    const counts = Array.from(provincesWithRecords.values());
    const maxCount = counts.length > 0 ? Math.max(...counts) : 1;
    console.log('[DEBUG] 最大访问次数:', maxCount);
    
    // 处理需要高亮的省份
    provincesWithRecords.forEach((count, province) => {
      console.log('[DEBUG] 处理省份高亮:', province, '访问次数:', count);
      
      // 标准化省份名称，确保与地图数据匹配
      let normalizedProvince = province;
      
      // 处理自治区、特别行政区等特殊名称
      if (province.includes('自治区')) {
        normalizedProvince = province.replace('自治区', '');
      } else if (province.includes('特别行政区')) {
        normalizedProvince = province.replace('特别行政区', '');
      }
      
      // 根据访问次数计算透明度，划分为五个区间
      let opacity, borderOpacity;
      const percentage = count / maxCount;
      
      if (percentage >= 0.8) { // 80-100%
        opacity = 0.8;
        borderOpacity = 1.0;
      } else if (percentage >= 0.6) { // 60-80%
        opacity = 0.65;
        borderOpacity = 0.85;
      } else if (percentage >= 0.4) { // 40-60%
        opacity = 0.5;
        borderOpacity = 0.75;
      } else if (percentage >= 0.2) { // 20-40%
        opacity = 0.35;
        borderOpacity = 0.65;
      } else { // 0-20%
        opacity = 0.2;
        borderOpacity = 0.5;
      }
      
      // 使用基于访问次数的高亮配置
      regions.push({
        name: normalizedProvince, // 确保name是字符串而不是数组
        itemStyle: {
          areaColor: `rgba(80, 120, 180, ${opacity})`,
          borderColor: `rgba(107, 142, 237, ${borderOpacity})`,
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: `rgba(107, 142, 237, ${borderOpacity * 0.7})`
        },
        emphasis: {
          itemStyle: {
            areaColor: `rgba(90, 140, 200, ${opacity + 0.2})`,
            borderColor: "rgba(107, 142, 237, 1)",
            borderWidth: 3,
            shadowBlur: 15,
            shadowColor: "rgba(107, 142, 237, 0.8)"
          }
        }
      });
    });
    
    // 添加南海诸岛特殊处理
    regions.push({
      name: "南海诸岛",
      itemStyle: {
        areaColor: "rgba(73,86,166,.1)",
        borderColor: "rgba(255,209,163, .5)",
        borderWidth: 1
      }
    });
    
    // 关键调试信息
    console.log('[DEBUG] 需要高亮的省份及访问次数:', Object.fromEntries(provincesWithRecords));
    console.log('[DEBUG] 生成的高亮区域配置:', regions);
    
    // 更新统计信息
    console.log('[DEBUG] 更新统计信息...');
    // 计算唯一城市数量（起点和终点去重）
    const allCities = new Set();
    array.forEach(route => {
      if (route.start) allCities.add(route.start);
      if (route.end) allCities.add(route.end);
    });
    const uniqueCityCount = allCities.size;
    const uniqueProvinceCount = provincesWithRecords.size;
    const totalRouteCount = array.length;
    
    console.log('[DEBUG] 统计结果 - 城市数:', uniqueCityCount, '省份数:', uniqueProvinceCount, '路线数:', totalRouteCount);
    
    // 更新DOM显示
    document.getElementById('city-count').textContent = uniqueCityCount;
    document.getElementById('province-count').textContent = uniqueProvinceCount;
    document.getElementById('route-count').textContent = totalRouteCount;
    
    // 确保地图geo配置存在
    if (!option.geo) {
      option.geo = {
        map: 'china'
      };
    }
    
    // 重置地图区域样式，避免样式叠加导致的问题
    if (!option.geo.itemStyle) {
      option.geo.itemStyle = {
        normal: {
          borderColor: "rgba(255,209,163, .5)",
          borderWidth: 1,
          areaColor: "rgba(73,86,166,.1)",
          borderWidth: 0.5,
          shadowBlur: 5,
          shadowColor: "rgba(107,91,237,.7)"
        }
      };
    }
    
    // 更新地图配置
    option.geo.regions = regions;
    option.series[1].data = plane_route;
    option.series[2].data = train_route;
    option.series[3].data = drive_route;
    option.series[4].data = bus_route;
    
    console.log('地图配置更新完成，应用到图表...');
    // 应用配置到图表，使用true强制更新
    myChart.setOption(option, true);
    
    // 手动触发重绘，确保样式正确应用
    setTimeout(function() {
      myChart.resize();
    }, 100);
  },
  error: function(xhr, status, error) {
    console.error('[DEBUG] 获取路线数据失败:', error);
  }
});

// 添加手动刷新地图的功能，便于调试
function refreshMap() {
  console.log('手动刷新地图...');
  // 重新应用当前配置
  myChart.setOption(option, true);
  myChart.resize();
}

// 为了方便调试，将refreshMap函数绑定到window对象
window.refreshMap = refreshMap;

// 更新地图函数 - 处理城市点、路线和省份高亮
function updateMap(cities, planeRoute, trainRoute, driveRoute, busRoute, provinces) {
  console.log('[DEBUG] 更新地图开始');
  console.log('[DEBUG] 城市数据:', cities ? cities.length : 0, '个城市');
  if (cities) {
    console.log('[DEBUG] 城市数据示例:', cities.slice(0, 3));
  }
  console.log('[DEBUG] 飞机路线:', planeRoute ? planeRoute.length : 0, '条');
  console.log('[DEBUG] 火车路线:', trainRoute ? trainRoute.length : 0, '条');
  console.log('[DEBUG] 自驾路线:', driveRoute ? driveRoute.length : 0, '条');
  console.log('[DEBUG] 公交路线:', busRoute ? busRoute.length : 0, '条');
  console.log('[DEBUG] 需要高亮的省份:', provinces ? Array.from(provinces) : []);
  
  // 确保option和geo配置存在
  if (!option) {
    console.error('option对象不存在！');
    return;
  }
  
  if (!option.geo) {
    option.geo = {
      map: 'china',
      roam: true,
      zoom: 1.2,
      regions: []
    };
  }
  
  // 首先确保series[0]存在且配置正确
  if (!option.series || !option.series[0]) {
    console.log('[DEBUG] 创建series[0]配置');
    option.series = option.series || [];
    option.series.unshift({
      type: "effectScatter",
      coordinateSystem: "geo",
      showEffectOn: "render",
      zlevel: 1,
      rippleEffect: {
        period: 15,
        scale: 4,
        brushType: "fill",
      },
      hoverAnimation: true,
      label: {
        normal: {
          formatter: "{b}",
          position: "right",
          color: "#F58158",
          show: true,
          fontSize: 12
        },
        emphasis: {
          show: true,
          fontSize: 14
        }
      },
      itemStyle: {
        normal: {
          color: "#f34e2b",
          borderColor: '#fff',
          borderWidth: 1,
          shadowBlur: 10,
          shadowColor: "#333",
        }
      },
      symbolSize: 8,
      data: []
    });
  }
  
  // 更新地图上的城市点
  if (cities && cities.length > 0) {
    console.log('[DEBUG] 开始处理城市点数据...');
    // 转换城市数据为echarts所需格式
    const formattedCities = cities.map(city => {
      const cityPoint = {
        name: city.name,
        value: [city.x || (city.value && city.value[0] ? city.value[0] : 0), 
                city.y || (city.value && city.value[1] ? city.value[1] : 0)],
        symbolSize: 8,
        itemStyle: {
          color: "#f34e2b",
          borderColor: '#fff',
          borderWidth: 1
        },
        label: {
          show: true,
          formatter: '{b}',
          position: 'right',
          color: '#f34e2b',
          fontSize: 12
        },
        province: city.province // 保留省份信息
      };
      console.log('[DEBUG] 格式化城市点:', cityPoint);
      return cityPoint;
    });
    
    // 更新全局points数组
    window.points = formattedCities;
    
    // 更新series[0]数据
    option.series[0].data = formattedCities;
    option.series[0].symbolSize = 8;
    option.series[0].label.show = true;
    
    console.log('[DEBUG] 城市点数据已更新到series[0]，共', formattedCities.length, '个点');
  } else {
    console.log('[DEBUG] 没有城市数据需要更新');
  }
  
  // 保留原始series结构，只更新数据而不删除系列
  // 这样可以保留各个路线系列的样式和配置
  
  // 更新飞机路线数据（如果系列存在）
  if (option.series[1] && planeRoute && planeRoute.length > 0) {
    option.series[1].data = planeRoute;
    console.log('飞机路线数据已更新:', planeRoute.length, '条');
  }
  
  // 更新火车路线数据（如果系列存在）
  if (option.series[2] && trainRoute && trainRoute.length > 0) {
    option.series[2].data = trainRoute;
    console.log('火车路线数据已更新:', trainRoute.length, '条');
  }
  
  // 更新自驾路线数据（如果系列存在）
  if (option.series[3] && driveRoute && driveRoute.length > 0) {
    option.series[3].data = driveRoute;
    console.log('自驾路线数据已更新:', driveRoute.length, '条');
  }
  
  // 更新公交路线数据（如果系列存在）
  if (option.series[4] && busRoute && busRoute.length > 0) {
    option.series[4].data = busRoute;
    console.log('公交路线数据已更新:', busRoute.length, '条');
  }
  
  // 省份高亮处理已经在AJAX请求的success回调中完成
  // updateMap函数不再重复处理省份高亮，避免冲突
  console.log('[DEBUG] 省份高亮配置保持不变，已在数据加载时完成处理');
  
  // 应用更新到图表
  console.log('[DEBUG] 地图配置更新完成，应用到图表...');
  if (myChart) {
    try {
      console.log('[DEBUG] 1. 检查当前图表状态');
      // 首先移除加载状态
      myChart.hideLoading();
      
      console.log('[DEBUG] 2. 验证series[0]数据状态:', option.series[0] ? option.series[0].data.length : '不存在');
      console.log('[DEBUG] 3. 验证geo配置状态:', option.geo ? option.geo.regions.length + '个地区' : '不存在');
      
      // 优先确保城市点配置正确
      console.log('[DEBUG] 3.1 优先设置城市点显示配置');
      if (option.series[0]) {
        // 确保城市点样式和标签配置正确
        option.series[0].symbolSize = 8;
        option.series[0].label = {
          normal: {
            show: true,
            formatter: '{b}',
            position: 'right',
            color: '#f34e2b',
            fontSize: 12
          },
          emphasis: {
            show: true,
            fontSize: 14
          }
        };
        option.series[0].zlevel = 10; // 提高层级确保显示在最上层
      }
      
      // 简化更新过程，一次性正确设置所有数据
      console.log('[DEBUG] 4. 应用完整地图配置...');
      
      // 首先清空之前的配置
      myChart.clear();
      
      // 重新设置整个option
      console.log('[DEBUG] 4.1 首次应用完整配置');
      myChart.setOption(option, true);
      
      // 强制重绘
      myChart.resize();
      
      // 短暂延迟后，再次应用配置以确保所有元素正确显示
      setTimeout(() => {
        console.log('[DEBUG] 5. 再次应用完整配置确保所有元素正确渲染');
        
        // 确保geo.regions配置在再次应用时仍然正确
        console.log('[DEBUG] 再次应用前的regions数量:', option.geo.regions.length);
        
        // 再次应用完整配置
        myChart.setOption(option, true);
        
        // 强制重绘
        myChart.clear();
        myChart.setOption(option, true);
        
        // 最后调整大小确保所有元素正确显示
        myChart.resize();
        console.log('[DEBUG] 6. 地图更新全部完成');
      }, 200);
      
    } catch (error) {
      console.error('[DEBUG] 应用地图配置时出错:', error);
    }
  } else {
    console.error('[DEBUG] myChart对象不存在！');
  }
}
