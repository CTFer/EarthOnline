/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2023-11-14 19:08:44
 * @LastEditTime: 2025-10-20 17:21:25
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2023 迷舍
 */
function addRoute(params) {
  $.ajax({
    url: "/route/add",
    data: params,
    async: true,
    dataType: "json",
    type: "post",
    success: function (array) {
      console.log(array);
    },
  });
}

function exchange(params) {
  var start = $(".start option:selected").val();
  var end = $(".end option:selected").val();

  form.val("route-form", {
    start: end,
    end: start,
  });
  form.render($("#route-form"));
}
function showList(array) {
  array = routes;
  html = "";
  for (let index = 0; index < array.length; index++) {
    const element = array[index];
    html += " <tr><td>" + new Date(element[0] * 1000).toLocaleString() + "</td><td>" + element[2] + "</td><td>" + element[3] + "</td><td>" + element[8] + "</td><tr>";
  }
  $(".list-content").html(html);
  layer.open({
    type: 1, // page 层类型
    area: ["800px", "600px"],
    title: "轨迹数据",
    shade: 0.3, // 遮罩透明度
    shadeClose: true, // 点击遮罩区域，关闭弹层
    maxmin: true, // 允许全屏最小化
    anim: 0, // 0-6 的动画形式，-1 不开启
    content:  $('#list-table'),
  });
}
