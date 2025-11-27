/*
 Navicat Premium Data Transfer

 Source Server         : 通讯录
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 19/11/2025 13:23:12
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for 通讯录
-- ----------------------------
DROP TABLE IF EXISTS "通讯录";
CREATE TABLE "通讯录" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "name" TEXT,
  "remark" INTEGER,
  "status" TEXT,
  "date" TEXT,
  "remark_1" TEXT,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------
-- Records of 通讯录
-- ----------------------------
INSERT INTO "通讯录" VALUES (1, '艾杰田', 13540003048, '退役军人2023', '1993-06-15', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (2, '艾力', 13880837778, '退役军人2023', '1982-01-22', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (3, '艾明飞', 15881109209, '退役军人2023', '1985-09-10', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (4, '艾明福', 15198208534, '退役军人2023', '1955-10-30', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (5, '艾同波', 15881012833, '退役军人2023', '1936-12-08', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (6, '艾巍', 13198506999, '退役军人2023', '1969-01-15', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (7, '艾伟', 13838235844, '退役军人2023', '1981-09-28', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (8, '艾文康', 13739489148, '退役军人2023', '1959-01-02', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (9, '艾文美', 13350874445, '退役军人2023', '1974-12-27', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (10, '艾希', 13548155414, '退役军人2023', '1980-08-17', NULL, '2025-11-14 08:03:50');
INSERT INTO "通讯录" VALUES (11, '艾永亮', 13688469175, '退役军人2023', '1950-03-10', NULL, '2025-11-14 08:03:50');

-- ----------------------------
-- Auto increment value for 通讯录
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 24041 WHERE name = '通讯录';

PRAGMA foreign_keys = true;
