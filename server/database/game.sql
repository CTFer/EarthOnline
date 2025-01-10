/*
 Navicat Premium Data Transfer

 Source Server         : game
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 10/01/2025 12:27:44
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for player_data
-- ----------------------------
DROP TABLE IF EXISTS "player_data";
CREATE TABLE "player_data" (
  "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  "user_id" INTEGER,
  "stamina" INTEGER DEFAULT 100,
  "strength" INTEGER DEFAULT 10,
  "intelligence" INTEGER DEFAULT 10,
  "player_name" TEXT,
  "create_time" integer,
  "level" integer,
  "experience" integer,
  UNIQUE ("user_id" ASC)
);

-- ----------------------------
-- Table structure for player_task
-- ----------------------------
DROP TABLE IF EXISTS "player_task";
CREATE TABLE "player_task" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "user_id" INTEGER,
  "task_id" INTEGER,
  "starttime" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "points_earned" INTEGER,
  "endtime" TIMESTAMP,
  "status" integer,
  FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("task_id") REFERENCES "tasks" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- ----------------------------
-- Table structure for skill_relations
-- ----------------------------
DROP TABLE IF EXISTS "skill_relations";
CREATE TABLE "skill_relations" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "parent_skill_id" INTEGER,
  "child_skill_id" INTEGER,
  "relation_type" TEXT,
  FOREIGN KEY ("parent_skill_id") REFERENCES "skills" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("child_skill_id") REFERENCES "skills" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  UNIQUE ("parent_skill_id" ASC, "child_skill_id" ASC)
);

-- ----------------------------
-- Table structure for skills
-- ----------------------------
DROP TABLE IF EXISTS "skills";
CREATE TABLE "skills" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" TEXT NOT NULL,
  "proficiency" INTEGER DEFAULT 0,
  "learned_time" DATETIME,
  "description" TEXT,
  "is_enabled" BOOLEAN DEFAULT 1,
  UNIQUE ("name" ASC)
);

-- ----------------------------
-- Table structure for sqlite_sequence
-- ----------------------------
DROP TABLE IF EXISTS "sqlite_sequence";
CREATE TABLE "sqlite_sequence" (
  "name",
  "seq"
);

-- ----------------------------
-- Table structure for tasks
-- ----------------------------
DROP TABLE IF EXISTS "tasks";
CREATE TABLE "tasks" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" TEXT NOT NULL,
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
  "task_scope" integer DEFAULT 0
);

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "users";
CREATE TABLE "users" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "username" TEXT NOT NULL,
  "password" TEXT NOT NULL,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "isadmin" BOOLEAN DEFAULT 0,
  UNIQUE ("username" ASC)
);

-- ----------------------------
-- Auto increment value for player_data
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 1 WHERE name = 'player_data';

-- ----------------------------
-- Auto increment value for player_task
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 10 WHERE name = 'player_task';

-- ----------------------------
-- Auto increment value for skill_relations
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 23 WHERE name = 'skill_relations';

-- ----------------------------
-- Auto increment value for skills
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 12 WHERE name = 'skills';

-- ----------------------------
-- Auto increment value for tasks
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 10 WHERE name = 'tasks';

-- ----------------------------
-- Auto increment value for users
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 2 WHERE name = 'users';

PRAGMA foreign_keys = true;
