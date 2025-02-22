/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-22 18:32:02
 * @LastEditTime: 2025-02-22 19:25:46
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
// cz-custom-adapter.js
module.exports = {
  // 当用户开始进行 commit 时，会调用这个函数来提示用户输入信息
  prompter: function (cz, commit) {
    console.log("\n第一行会裁剪到100个字符，其他行会裁剪到100个字符.\n");

    // 定义一些提示信息
    const questions = [
      {
        type: "list",
        name: "type",
        message: "选择 commit 类型:",
        choices: [
          { name: "🎨:art: 改进代码结构/代码格式", value: "🎨:art:" },
          { name: "⚡️:zap: 提升性能", value: "⚡️:zap:" },
          { name: "🔥:fire: 移除代码或文件", value: "🔥:fire:" },
          { name: "🐛:bug: 修复 bug", value: "🐛:bug:" },
          { name: "🚑:ambulance: 重要补丁", value: "🚑:ambulance:" },
          { name: "✨:sparkles: 引入新功能", value: "✨:sparkles:" },
          { name: "📝:memo: 撰写文档", value: "📝:memo:" },
          { name: "🚀:rocket: 部署功能", value: "🚀:rocket:" },
          { name: "💄:lipstick: 更新 UI 和样式文件", value: "💄:lipstick:" },
          { name: "🎉:tada: 初次提交", value: "🎉:tada:" },
          { name: "✅:white_check_mark: 增加测试", value: "✅:white_check_mark:" },
          { name: "🔖:bookmark: 发行/版本标签", value: "🔖:bookmark:" },
          { name: "🚧:construction: 工作进行中", value: "🚧:construction:" },
          { name: "⬇️:arrow_down: 降级依赖", value: "⬇️:arrow_down:" },
          { name: "⬆️:arrow_up: 升级依赖", value: "⬆️:arrow_up:" },
          { name: "📈:chart_with_upwards_trend: 添加分析或跟踪代码", value: "📈:chart_with_upwards_trend:" },
          { name: "🔨:hammer: 重大重构", value: "🔨:hammer:" },
          { name: "🔧:wrench: 修改配置文件", value: "🔧:wrench:" },
          { name: "🌐:globe_with_meridians: 国际化与本地化", value: "🌐:globe_with_meridians:" },
        ],
        default: "🐛:bug:",
      },
      {
        type: "input",
        name: "version",
        message: "输入版本号 (如 V0.2.12):",
        default: "V0.0.0",
        validate: function (input) {
          return input.startsWith("V") ? true : "版本号必须以 V 开头";
        },
      },
      {
        type: "input",
        name: "subject",
        message: "输入 commit 简短描述 (不超过 100 字符):",
        validate: function (input) {
          return input.length <= 100 ? true : "描述不能超过 100 字符";
        },
      },
      {
        type: "editor",
        name: "body",
        message: "输入详细的 commit 信息 (可选，按回车跳过):",
      },
      {
        type: "input",
        name: "knownBugs",
        message: "输入已知 BUG (可选，按回车跳过):",
      },
    ];

    // 使用 cz 对象的 prompt 方法来提示用户输入信息
    cz.prompt(questions).then(function (answers) {
      const type = answers.type;
      const version = answers.version;
      const subject = answers.subject;
      const body = answers.body ? "\n\n" + answers.body : "";
      const knownBugs = answers.knownBugs ? "\n\n已知 BUG:\n" + answers.knownBugs : "";

      // 生成最终的 commit 信息
      const message = `${type}(${version}): ${subject}${body}${knownBugs}`;

      // 调用 commit 函数提交信息
      commit(message);
    });
  },
};
