-- 简单版本：更新广告位position字段
ALTER TABLE `advertisements` 
MODIFY COLUMN `position` enum(
    'search_list',
    'article_detail', 
    'both',
    'homepage-middle',
    'homepage-resources',
    'article-middle',
    'article-sidebar',
    'home-banner',
    'sidebar'
) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '广告位置';
