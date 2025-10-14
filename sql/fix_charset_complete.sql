-- 完整修复数据库中文乱码问题
-- 执行时间：2025-01-13

-- 设置会话字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 1. 检查当前状态
SELECT '=== 当前数据库字符集 ===' as info;
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'tg2em';

SELECT '=== 当前表字符集 ===' as info;
SELECT 
    TABLE_NAME as 'Table',
    TABLE_COLLATION as 'Collation'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'tg2em' AND TABLE_NAME = 'advertisements';

-- 2. 修复数据库字符集
ALTER DATABASE tg2em CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. 修复advertisements表的字符集
ALTER TABLE advertisements CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 4. 修复system_config表的字符集（如果存在）
ALTER TABLE system_config CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. 修复messages表的字符集（如果存在）
ALTER TABLE messages CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 6. 验证修复结果
SELECT '=== 修复后数据库字符集 ===' as info;
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'tg2em';

SELECT '=== 修复后表字符集 ===' as info;
SELECT 
    TABLE_NAME as 'Table',
    TABLE_COLLATION as 'Collation'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'tg2em' 
AND TABLE_NAME IN ('advertisements', 'system_config', 'messages');

-- 7. 测试中文插入（可选）
-- 取消注释下面的代码来测试中文插入
/*
INSERT INTO advertisements (name, position, ad_code, is_active) 
VALUES ('测试中文广告位', 'home-banner', '<div>测试中文内容</div>', 1);

SELECT * FROM advertisements WHERE name LIKE '%测试%';
*/
