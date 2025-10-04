-- 添加 tgstate_url 配置参数到现有数据库
-- 如果不存在则插入，如果存在则更新描述

INSERT INTO `system_config` (`config_key`, `config_value`, `config_type`, `description`, `category`) 
VALUES ('tgstate_url', 'http://localhost:8088', 'string', 'tgState 基础URL地址', 'tgstate')
ON DUPLICATE KEY UPDATE 
    `description` = 'tgState 基础URL地址',
    `config_type` = 'string',
    `category` = 'tgstate';
