-- Nginx Proxy Manager 数据库初始化脚本

-- 创建 npm 数据库
CREATE DATABASE IF NOT EXISTS `npm` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建 npm 用户并授权
CREATE USER IF NOT EXISTS 'npm'@'%' IDENTIFIED BY 'npm';
GRANT ALL PRIVILEGES ON `npm`.* TO 'npm'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
