/*
 Navicat Premium Data Transfer

 Source Server         : game
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 13/01/2025 23:25:19
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for tasks
-- ----------------------------
DROP TABLE IF EXISTS "tasks";
CREATE TABLE "tasks" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
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
  "task_chain_id" INTEGER,
  "icon" TEXT
);

-- ----------------------------
-- Auto increment value for tasks
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 10 WHERE name = 'tasks';

PRAGMA foreign_keys = true;
