-- 修复数据库中文乱码问题
-- 执行时间：2025-01-13

-- 1. 检查当前数据库和表的字符集
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'tg2em';

-- 2. 检查advertisements表的字符集
SELECT 
    TABLE_NAME as 'Table',
    TABLE_COLLATION as 'Collation'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'tg2em' AND TABLE_NAME = 'advertisements';

-- 3. 检查advertisements表各字段的字符集
SELECT 
    COLUMN_NAME as 'Column',
    CHARACTER_SET_NAME as 'Charset',
    COLLATION_NAME as 'Collation'
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'tg2em' 
AND TABLE_NAME = 'advertisements' 
AND CHARACTER_SET_NAME IS NOT NULL;

-- 4. 修复数据库字符集
ALTER DATABASE tg2em CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. 修复advertisements表的字符集
ALTER TABLE advertisements CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 6. 验证修复结果
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'tg2em';

-- 7. 检查修复后的表字符集
SELECT 
    TABLE_NAME as 'Table',
    TABLE_COLLATION as 'Collation'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'tg2em' AND TABLE_NAME = 'advertisements';
