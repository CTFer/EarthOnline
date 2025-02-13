/*
 Navicat Premium Data Transfer

 Source Server         : game
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 13/02/2025 11:58:51
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for roadmap
-- ----------------------------
DROP TABLE IF EXISTS "roadmap";
CREATE TABLE "roadmap" (
  "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" TEXT,
  "description" TEXT,
  "addtime" integer,
  "edittime" integer,
  "status" TEXT,
  "color" TEXT,
  "order" integer
);

-- ----------------------------
-- Records of roadmap
-- ----------------------------
INSERT INTO "roadmap" VALUES (1, '重构代码', '重构前端js代码', 1739417227, 1739418181, 'DEVELOPING', '', -1);
INSERT INTO "roadmap" VALUES (2, '人物形象支持配置live2d和静态图片', '', 1739417907, 1739418673, 'PLANNED', '#16b777', 1);
INSERT INTO "roadmap" VALUES (3, 'NFC读写解决适配NFCTools问题', '', 1739418202, 1739418202, 'COMPLETED', '#ffffff', 1);
INSERT INTO "roadmap" VALUES (4, 'NFC读写数据同步到远端服务器问题', '', 1739418211, 1739418377, 'PLANNED', '#fafafa', 2);
INSERT INTO "roadmap" VALUES (5, 'GPS位置信息记录', '', 1739418217, 1739418217, 'COMPLETED', '#ffffff', 3);
INSERT INTO "roadmap" VALUES (6, '左侧面板优化', '', 1739418225, 1739418677, 'PLANNED', '#16b777', 4);
INSERT INTO "roadmap" VALUES (7, '地图显示优化', '', 1739418422, 1739418422, 'PLANNED', '#16b777', 5);
INSERT INTO "roadmap" VALUES (8, '卡片写入乱码问题', '愚蠢 是读取代码的问题 而非写入的问题', 1739418445, 1739418445, 'COMPLETED', '#ff5722', 6);
INSERT INTO "roadmap" VALUES (9, 'NFC读写数据同步到远端服务器问题', '', 1739418473, 1739418473, 'PLANNED', '#ffffff', 7);
INSERT INTO "roadmap" VALUES (10, '男孩女孩使用不同主题', '', 1739418527, 1739418680, 'PLANNED', '#16b777', 8);
INSERT INTO "roadmap" VALUES (11, '任务支持添加每日任务', '比如坚持一个月锻炼，则添加重复30次的每日任务。通过统计玩家表中complete的数量来判断任务是否完成', 1739418543, 1739418669, 'PLANNED', '#fafafa', 0);
INSERT INTO "roadmap" VALUES (12, '商品管理页面', '添加编辑商品字段', 1739418564, 1739418564, 'PLANNED', '#ffffff', 9);
INSERT INTO "roadmap" VALUES (13, '添加玩家背包显示', '优化商品列表页', 1739418579, 1739418579, 'PLANNED', '#ffffff', 10);
INSERT INTO "roadmap" VALUES (14, '切换运行环境到fastapi', '', 1739418588, 1739418588, 'PLANNED', '#ffffff', 11);
INSERT INTO "roadmap" VALUES (15, '完善任务发布面板 ', 'NFC数据生成到卡片', 1739418619, 1739418621, 'PLANNED', '#ffffff', 4);
INSERT INTO "roadmap" VALUES (16, '主线任务设计', '', 1739418638, 1739418638, 'PLANNED', '#1e9fff', 12);
INSERT INTO "roadmap" VALUES (17, '随机事件系统', '摇骰子系统，添加随机事件', 1739418662, 1739418662, 'PLANNED', '#fafafa', 13);
INSERT INTO "roadmap" VALUES (18, 'ipv6/v4支持', '', 1739418694, 1739418694, 'PLANNED', '#fafafa', 14);
INSERT INTO "roadmap" VALUES (19, '工具软件', ' 背单词等', 1739418710, 1739418710, 'PLANNED', '#ffffff', 15);
INSERT INTO "roadmap" VALUES (20, '声音识别', '任务接取 任务完成 玩家验证', 1739418734, 1739418734, 'PLANNED', '#ffffff', 16);
INSERT INTO "roadmap" VALUES (21, '任务的完成与后续任务的开放', '', 1739418754, 1739418754, 'PLANNED', '#ffffff', 17);
INSERT INTO "roadmap" VALUES (22, '远端GPS数据同步到本地', '', 1739418766, 1739418766, 'PLANNED', '#ffffff', 18);

-- ----------------------------
-- Auto increment value for roadmap
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 22 WHERE name = 'roadmap';

PRAGMA foreign_keys = true;
