-- ============================================================================
-- Aurora Private Deployment - Database Schema
-- ============================================================================
-- 初始化数据库架构，创建所有必要的表

-- ============================================================================
-- 用户相关表
-- ============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255),
    password_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- ============================================================================
-- 项目相关表
-- ============================================================================

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_account_id ON projects(account_id);

-- 为本地部署增加管理员标记字段
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Agent 相关表
-- ============================================================================

-- 代理表
CREATE TABLE IF NOT EXISTS agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT,
    model VARCHAR(255),
    icon_name VARCHAR(255),
    icon_color VARCHAR(255),
    icon_background VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    version_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_agents_account_id ON agents(account_id);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at);
CREATE INDEX IF NOT EXISTS idx_agents_is_default ON agents(account_id, is_default) WHERE is_default = true;

-- ============================================================================
-- Thread/Conversation 相关表
-- ============================================================================

-- 对话线程表
CREATE TABLE IF NOT EXISTS threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(agent_id) ON DELETE SET NULL,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    initialization_started_at TIMESTAMP WITHOUT TIME ZONE,
    initialization_error TEXT,
    initialization_completed_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_threads_account_id ON threads(account_id);
CREATE INDEX IF NOT EXISTS idx_threads_agent_id ON threads(agent_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text', -- 'text', 'tool_call', 'tool_result'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- ============================================================================
-- 工具执行相关表
-- ============================================================================

-- 工具调用表
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_thread_id ON tool_calls(thread_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_status ON tool_calls(status);

-- ============================================================================
-- 实时更新表（用于 WebSocket 实时通知）
-- ============================================================================

-- 用户在线状态表
CREATE TABLE IF NOT EXISTS user_presence_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES threads(thread_id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_presence_user_id ON user_presence_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_presence_thread_id ON user_presence_sessions(thread_id);

-- ============================================================================
-- API Key 表（用于认证）
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- ============================================================================
-- 创建更新时间自动更新触发器
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为各表创建触发器（先删除已存在的，避免重复创建错误）
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_threads_updated_at ON threads;
CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_presence_updated_at ON user_presence_sessions;
CREATE TRIGGER update_presence_updated_at BEFORE UPDATE ON user_presence_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 创建初始管理员用户（可选）
-- ============================================================================
-- 密码: admin123 (需要在实际使用时更改！)
-- INSERT INTO users (email, username, password_hash, is_active) 
-- VALUES ('admin@aurora.local', 'admin', '$2b$12$...', true);

-- ============================================================================
-- 用户角色表
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, role)
);
