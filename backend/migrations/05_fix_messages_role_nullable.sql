-- ============================================================================
-- 修复 messages 表 role 列约束
-- ============================================================================
-- 允许 role 列为 NULL，因为 status/llm_response_start/llm_response_end 等
-- 类型的消息不需要 role 字段

BEGIN;

-- 移除 role 列的 NOT NULL 约束
ALTER TABLE messages 
ALTER COLUMN role DROP NOT NULL;

-- 添加注释说明
COMMENT ON COLUMN messages.role IS 'Message role (user/assistant/system). NULL for status/llm_response messages';

COMMIT;
