-- 测试中文插入和查询
-- 执行时间：2025-01-13

-- 设置会话字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 1. 插入测试中文数据
INSERT INTO advertisements (name, position, ad_code, is_active, sort_order) 
VALUES (
    '测试中文广告位', 
    'home-banner', 
    '<div>这是测试中文广告代码</div>', 
    1, 
    999
);

-- 2. 查询测试数据
SELECT 
    id,
    name,
    position,
    is_active,
    created_at
FROM advertisements 
WHERE name LIKE '%测试%'
ORDER BY id DESC;

-- 3. 删除测试数据（可选）
-- DELETE FROM advertisements WHERE name = '测试中文广告位';
