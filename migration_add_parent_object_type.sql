-- 对象类型增加 parent_object_type 字段，支持子对象类型层级关系
-- 执行时间：2026-05-01

-- 1. 新增 parent_object_type 字段
ALTER TABLE `object_types`
  ADD COLUMN `parent_object_type` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '父对象类型ID，NULL表示一级对象类型'
  AFTER `database_name`;

-- 2. 为 parent_object_type 添加索引，提高子对象类型查询性能
ALTER TABLE `object_types`
  ADD INDEX `idx_parent_object_type` (`parent_object_type`);

-- 3. 现有数据默认为一级对象类型（parent_object_type 已为 NULL，无需更新）
-- UPDATE object_types SET parent_object_type = NULL;
