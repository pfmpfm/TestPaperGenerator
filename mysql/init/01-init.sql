-- 初始化数据库
CREATE DATABASE IF NOT EXISTS exam_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE exam_generator;

-- 设置时区
SET time_zone = '+08:00';

-- 创建健康检查用户 (可选)
-- CREATE USER IF NOT EXISTS 'healthcheck'@'%' IDENTIFIED BY 'healthcheck';
-- GRANT SELECT ON exam_generator.* TO 'healthcheck'@'%';
-- FLUSH PRIVILEGES;
