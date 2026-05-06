-- 对象类型增加 object_type_category 字段，区分实体对象类型和关系对象类型
-- 执行时间：2026-05-03

ALTER TABLE `object_types`
  ADD COLUMN `object_type_category` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'entity' COMMENT '对象类型分类：entity=实体对象类型，relation=关系对象类型';
