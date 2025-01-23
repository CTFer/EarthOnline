/*
 Navicat Premium Data Transfer

 Source Server         : game
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 22/01/2025 15:55:35
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for tasks
-- ----------------------------
DROP TABLE IF EXISTS "tasks";
CREATE TABLE "tasks" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "task_chain_id" INTEGER,
  "name" TEXT,
  "description" TEXT,
  "points" INTEGER DEFAULT 0,
  "stamina_cost" INTEGER DEFAULT 0,
  "is_enabled" BOOLEAN DEFAULT 1,
  "repeatable" BOOLEAN DEFAULT 0,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "task_type" text,
  "task_rewards" text,
  "task_status" integer,
  "limit_time" integer,
  "task_scope" integer DEFAULT 0,
  "repeat_time" integer DEFAULT 0,
  "publisher" integer DEFAULT 1,
  "icon" TEXT DEFAULT 0,
  "parent_task_id" INTEGER
);

-- ----------------------------
-- Records of tasks
-- ----------------------------
INSERT INTO "tasks" VALUES (1, 0, '每日阅读', '完成30分钟阅读', 100, 20, 1, 1, '2025-01-06 14:07:10', 'DAILY', NULL, 'AVAILABLE', NULL, 1, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (2, 0, '小学文凭', '完成小学教育', 150, 30, 1, 1, '2025-01-06 14:07:10', 'BRANCH', '{"points_rewards": [{"type": "exp", "number": 0}, {"type": "points", "number": 0}], "card_rewards": [{"id": 0, "number": 0}], "medal_rewards": [{"id": 0, "number": 0}]}', NULL, 0, 0, 1, 1, NULL, 0);
INSERT INTO "tasks" VALUES (3, 0, '冥想', '进行15分钟冥想', 50, 10, 1, 1, '2025-01-06 14:07:10', 'DAILY', NULL, 'AVAILABLE', NULL, 0, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (4, 0, '技能培训', '参加一次技能培训课程', 200, 40, 1, 0, '2025-01-06 14:07:10', 'SPECIAL', NULL, 'AVAILABLE', NULL, 2, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (5, 2, '志愿服务', '参与社区志愿服务', 300, 50, 1, 1, '2025-01-06 14:07:10', 'SPECIAL', '{"points_rewards": [{"type": "exp", "number": 10}, {"type": "points", "number": 10}], "card_rewards": [{"id": 0, "number": 0}], "medal_rewards": [{"id": 0, "number": 0}]}', NULL, 0, 0, 1, 1, NULL, 1);
INSERT INTO "tasks" VALUES (6, 2, '每日锻炼1', '完成30分钟体能训练', 100, 20, 1, 1, '2025-01-07 03:00:50', 'DAILY', '{"points_rewards": [{"name": "exp", "number": 0}, {"name": "points", "number": 0}], "card_rewards": [{"name": "item", "id": 0, "number": 0}], "medal_rewards": [{"name": "exp", "id": 0, "number": 0}]}', 'AVAILABLE', 0, 0, 0, 1, NULL, 5);
INSERT INTO "tasks" VALUES (7, 0, '阅读学习', '阅读一小时专业书籍', 150, 30, 1, 1, '2025-01-07 03:00:50', 'DAILY', NULL, 'AVAILABLE', NULL, 0, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (8, 0, '冥想', '进行15分钟冥想', 50, 10, 1, 1, '2025-01-07 03:00:50', 'DAILY', NULL, 'AVAILABLE', NULL, 0, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (9, 0, '技能培训', '参加一次技能培训课程', 200, 40, 1, 0, '2025-01-07 03:00:50', 'BRANCH', NULL, 'AVAILABLE', NULL, 0, 0, 1, NULL, NULL);
INSERT INTO "tasks" VALUES (10, 2, '志愿服务', '参与社区志愿服务', 300, 50, 1, 1, '2025-01-07 03:00:50', 'BRANCH', '{"points_rewards": [{"type": "exp", "number": 0}, {"type": "points", "number": 0}], "card_rewards": [{"id": 0, "number": 0}], "medal_rewards": [{"id": 0, "number": 0}]}', NULL, 0, 0, 1, 1, NULL, 11);
INSERT INTO "tasks" VALUES (11, 1, '幼儿园初体验', '第一天走进幼儿园，认识新朋友，学会和小伙伴们打招呼', 0, 20, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":100}],"card_rewards":[],"medal_rewards":[]}', 'IN_PROGRESS', 0, 0, 0, 1, 0, 0);
INSERT INTO "tasks" VALUES (12, 1, '自理小能手', '学会自己穿衣服、叠被子、整理书包', 0, 30, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":150}],"card_rewards":[],"medal_rewards":[]}', 'IN_PROGRESS', 0, 0, 0, 1, 0, 11);
INSERT INTO "tasks" VALUES (13, 1, '文字启蒙', '认识100个汉字，学会写自己的名字', 0, 40, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":200}],"card_rewards":[],"medal_rewards":[]}', 'IN_PROGRESS', 0, 0, 0, 1, 0, 12);
INSERT INTO "tasks" VALUES (14, 1, '数学入门', '掌握20以内的加减法，认识简单的几何图形', 0, 40, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":200}],"card_rewards":[],"medal_rewards":[]}', 'IN_PROGRESS', 0, 0, 0, 1, 0, 13);
INSERT INTO "tasks" VALUES (15, 1, '小学新生活', '适应小学生活，学会按时完成作业', 0, 50, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":300}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 14);
INSERT INTO "tasks" VALUES (16, 1, '拼音大通关', '掌握拼音规则，能够准确拼读汉字', 0, 50, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":300}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 15);
INSERT INTO "tasks" VALUES (17, 1, '作文初探', '学会写简单的观察日记和周记', 0, 60, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":400}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 16);
INSERT INTO "tasks" VALUES (18, 1, '乘除运算', '掌握乘法口诀表，学会简单的除法', 0, 60, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":400}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 17);
INSERT INTO "tasks" VALUES (19, 1, '英语启航', '学会26个英文字母，掌握简单的英语单词', 0, 70, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":500}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 18);
INSERT INTO "tasks" VALUES (20, 1, '科学探索', '了解自然现象，进行简单的科学实验', 0, 70, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":500}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 19);
INSERT INTO "tasks" VALUES (21, 1, '初中预备', '完成小学学业，准备迎接初中生活', 0, 80, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":600}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 20);
INSERT INTO "tasks" VALUES (22, 1, '初中适应', '适应新的学习节奏，掌握科学的学习方法', 0, 90, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":700}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 21);
INSERT INTO "tasks" VALUES (23, 1, '代数基础', '掌握基础代数运算，学会解简单方程', 0, 100, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":800}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 22);
INSERT INTO "tasks" VALUES (24, 1, '物理入门', '理解基本物理概念，完成简单实验', 0, 100, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":800}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 23);
INSERT INTO "tasks" VALUES (25, 1, '化学探索', '学习化学基础知识，进行安全实验', 0, 110, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":900}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 24);
INSERT INTO "tasks" VALUES (26, 1, '中考冲刺', '系统复习，全力准备中考', 0, 120, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":1000}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 25);
INSERT INTO "tasks" VALUES (27, 1, '高中起航', '适应高中生活，制定合理的学习计划', 0, 130, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":1200}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 26);
INSERT INTO "tasks" VALUES (28, 1, '理科深入', '深入学习理科知识，培养科学思维', 0, 140, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":1500}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 27);
INSERT INTO "tasks" VALUES (29, 1, '文科积累', '积累文科知识，提升人文素养', 0, 140, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":1500}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 28);
INSERT INTO "tasks" VALUES (30, 1, '高考准备', '系统复习，调整心态，准备高考', 0, 150, 1, 0, '2025-01-15 13:18:46', 'MAIN', '{"points_rewards":[{"name":"exp","number":2000}],"card_rewards":[],"medal_rewards":[]}', 'AVAILABLE', 0, 0, 0, 1, 0, 29);

-- ----------------------------
-- Auto increment value for tasks
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 30 WHERE name = 'tasks';

PRAGMA foreign_keys = true;
