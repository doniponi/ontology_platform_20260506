-- 对象类型增加 show_parent_link 字段，控制图谱中是否展示父子连接线
-- 执行时间：2026-05-02

ALTER TABLE `object_types`
  ADD COLUMN `show_parent_link` tinyint(1) DEFAULT 1 COMMENT '是否在图谱中显示包含子对象类型连接线，1=显示，0=不显示';
