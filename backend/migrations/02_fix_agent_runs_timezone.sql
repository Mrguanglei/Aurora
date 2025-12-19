-- ============================================================================
-- 修复 agent_runs 表的 timezone 问题
-- ============================================================================

-- 将 agent_runs 表的 timestamp 字段从 timestamp without time zone 改为 timestamp with time zone
ALTER TABLE agent_runs
ALTER COLUMN started_at TYPE TIMESTAMP WITH TIME ZONE USING started_at AT TIME ZONE 'UTC';

ALTER TABLE agent_runs
ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE USING completed_at AT TIME ZONE 'UTC';

ALTER TABLE agent_runs
ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE agent_runs
ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

-- 修改默认值为 CURRENT_TIMESTAMP(自动使用 UTC)
ALTER TABLE agent_runs
ALTER COLUMN started_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE agent_runs
ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE agent_runs
ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
