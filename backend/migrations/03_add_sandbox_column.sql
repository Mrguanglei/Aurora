-- ============================================================================
-- 添加 sandbox 列到 projects 表
-- ============================================================================
-- 这个迁移为本地 PostgreSQL 部署添加 sandbox 支持

BEGIN;

-- 为 projects 表添加 sandbox 列
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS sandbox JSONB DEFAULT '{}'::jsonb;

-- 添加 description 列（如果不存在）
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS description TEXT;

-- 添加 updated_at 列（如果不存在）
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 添加触发器（如果不存在）
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加 is_public 列的索引
CREATE INDEX IF NOT EXISTS idx_projects_is_public ON projects(is_public);

-- 添加注释
COMMENT ON COLUMN projects.sandbox IS 'Sandbox metadata including id, password, VNC URL, and website URL';
COMMENT ON COLUMN projects.description IS 'Project description';

COMMIT;
