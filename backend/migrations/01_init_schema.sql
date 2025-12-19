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

-- 添加头像 URL 字段
ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar_url TEXT;

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
    current_version_id UUID,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_agents_account_id ON agents(account_id);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at);
CREATE INDEX IF NOT EXISTS idx_agents_is_default ON agents(account_id, is_default) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_agents_current_version ON agents(current_version_id);

-- ============================================================================
-- Thread/Conversation 相关表
-- ============================================================================

-- 对话线程表
CREATE TABLE IF NOT EXISTS threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(agent_id) ON DELETE SET NULL,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    initialization_started_at TIMESTAMP WITH TIME ZONE,
    initialization_error TEXT,
    initialization_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP WITH TIME ZONE
);

-- 修复现有表的列类型（如果表已存在）
ALTER TABLE threads
ALTER COLUMN initialization_started_at TYPE TIMESTAMP WITH TIME ZONE USING initialization_started_at AT TIME ZONE 'UTC';

ALTER TABLE threads
ALTER COLUMN initialization_completed_at TYPE TIMESTAMP WITH TIME ZONE USING initialization_completed_at AT TIME ZONE 'UTC';

-- 为现有表添加 project_id 列（如果不存在）
ALTER TABLE threads
ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_threads_account_id ON threads(account_id);
CREATE INDEX IF NOT EXISTS idx_threads_project_id ON threads(project_id);
CREATE INDEX IF NOT EXISTS idx_threads_agent_id ON threads(agent_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);


-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50), -- 'user', 'assistant', 'system' (允许为 NULL，因为 status/llm_response 类型消息不需要 role)
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

DROP TRIGGER IF EXISTS update_agent_versions_updated_at ON agent_versions;
CREATE TRIGGER update_agent_versions_updated_at BEFORE UPDATE ON agent_versions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_memories_updated_at ON user_memories;
CREATE TRIGGER update_user_memories_updated_at BEFORE UPDATE ON user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_kb_folders_updated_at ON knowledge_base_folders;
CREATE TRIGGER update_kb_folders_updated_at BEFORE UPDATE ON knowledge_base_folders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_kb_entries_updated_at ON knowledge_base_entries;
CREATE TRIGGER update_kb_entries_updated_at BEFORE UPDATE ON knowledge_base_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_credential_profiles_updated_at ON user_mcp_credential_profiles;
CREATE TRIGGER update_credential_profiles_updated_at BEFORE UPDATE ON user_mcp_credential_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 添加外键约束（需要在相关表创建后）
-- ============================================================================

-- 为agents.current_version_id添加外键
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_agents_current_version'
    ) THEN
        ALTER TABLE agents 
        ADD CONSTRAINT fk_agents_current_version 
        FOREIGN KEY (current_version_id) 
        REFERENCES agent_versions(version_id);
    END IF;
END $$;

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

-- ============================================================================
-- Agent版本管理表
-- ============================================================================

-- Agent版本表
CREATE TABLE IF NOT EXISTS agent_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_name VARCHAR(50) NOT NULL,
    system_prompt TEXT NOT NULL,
    model VARCHAR(255),
    configured_mcps JSONB DEFAULT '[]'::jsonb,
    custom_mcps JSONB DEFAULT '[]'::jsonb,
    agentpress_tools JSONB DEFAULT '{}'::jsonb,
    config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    UNIQUE(agent_id, version_number),
    UNIQUE(agent_id, version_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_id ON agent_versions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_versions_is_active ON agent_versions(is_active);

-- Agent版本历史记录表
CREATE TABLE IF NOT EXISTS agent_version_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES agent_versions(version_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    change_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_version_history_agent_id ON agent_version_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_version_history_version_id ON agent_version_history(version_id);

-- ============================================================================
-- 用户记忆系统表
-- ============================================================================

-- 创建枚举类型
DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('fact', 'preference', 'context', 'conversation_summary');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE memory_extraction_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 用户记忆表
CREATE TABLE IF NOT EXISTS user_memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    memory_type memory_type NOT NULL DEFAULT 'fact',
    source_thread_id UUID REFERENCES threads(thread_id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.8,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memories_account_id ON user_memories(account_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_source_thread ON user_memories(source_thread_id);

-- 记忆提取队列表
CREATE TABLE IF NOT EXISTS memory_extraction_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_ids JSONB NOT NULL DEFAULT '[]',
    status memory_extraction_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_memory_queue_account_id ON memory_extraction_queue(account_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_thread_id ON memory_extraction_queue(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_status ON memory_extraction_queue(status);

-- ============================================================================
-- 知识库系统表
-- ============================================================================

-- 知识库文件夹表
CREATE TABLE IF NOT EXISTS knowledge_base_folders (
    folder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT kb_folders_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_kb_folders_account_id ON knowledge_base_folders(account_id);

-- 知识库条目表
CREATE TABLE IF NOT EXISTS knowledge_base_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_id UUID NOT NULL REFERENCES knowledge_base_folders(folder_id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(255),
    
    summary TEXT NOT NULL,
    usage_context VARCHAR(100) DEFAULT 'always' CHECK (usage_context IN ('always', 'on_request', 'contextual')),
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_entries_folder_id ON knowledge_base_entries(folder_id);
CREATE INDEX IF NOT EXISTS idx_kb_entries_account_id ON knowledge_base_entries(account_id);

-- Agent知识库分配表
CREATE TABLE IF NOT EXISTS agent_knowledge_entry_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    entry_id UUID NOT NULL REFERENCES knowledge_base_entries(entry_id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    enabled BOOLEAN DEFAULT TRUE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(agent_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_kb_entry_assignments_agent_id ON agent_knowledge_entry_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_kb_entry_assignments_entry_id ON agent_knowledge_entry_assignments(entry_id);

-- ============================================================================
-- MCP凭证配置表
-- ============================================================================

-- 用户MCP凭证配置表
CREATE TABLE IF NOT EXISTS user_mcp_credential_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mcp_qualified_name TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    encrypted_config TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(account_id, mcp_qualified_name, profile_name)
);

CREATE INDEX IF NOT EXISTS idx_credential_profiles_account_mcp 
    ON user_mcp_credential_profiles(account_id, mcp_qualified_name);

CREATE INDEX IF NOT EXISTS idx_credential_profiles_account_active 
    ON user_mcp_credential_profiles(account_id, is_active) 
    WHERE is_active = true;

-- ============================================================================
-- 辅助函数
-- ============================================================================

-- 获取用户记忆统计函数
CREATE OR REPLACE FUNCTION get_memory_stats(p_account_id UUID)
RETURNS TABLE(
    total_memories INTEGER,
    fact_count INTEGER,
    preference_count INTEGER,
    context_count INTEGER,
    summary_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_memories,
        COUNT(*) FILTER (WHERE memory_type = 'fact')::INTEGER as fact_count,
        COUNT(*) FILTER (WHERE memory_type = 'preference')::INTEGER as preference_count,
        COUNT(*) FILTER (WHERE memory_type = 'context')::INTEGER as context_count,
        COUNT(*) FILTER (WHERE memory_type = 'conversation_summary')::INTEGER as summary_count
    FROM user_memories
    WHERE account_id = p_account_id;
END;
$$ LANGUAGE plpgsql;

-- 获取Agent知识库上下文函数
CREATE OR REPLACE FUNCTION get_agent_knowledge_base_context(
    p_agent_id UUID,
    p_max_tokens INTEGER DEFAULT 10000
)
RETURNS TEXT AS $$
DECLARE
    context_text TEXT := '';
    entry_record RECORD;
    current_tokens INTEGER := 0;
BEGIN
    FOR entry_record IN
        SELECT 
            e.entry_id,
            e.filename,
            e.summary
        FROM knowledge_base_entries e
        INNER JOIN agent_knowledge_entry_assignments a 
            ON e.entry_id = a.entry_id
        WHERE a.agent_id = p_agent_id
        AND a.enabled = TRUE
        AND e.is_active = TRUE
        AND e.usage_context IN ('always', 'contextual')
        ORDER BY e.created_at DESC
    LOOP
        -- 简单估算: 1 token ≈ 4 characters
        IF current_tokens + (LENGTH(entry_record.summary) / 4) > p_max_tokens THEN
            EXIT;
        END IF;
        
        context_text := context_text || E'\n\n## ' || entry_record.filename || E'\n';
        context_text := context_text || entry_record.summary;
        
        current_tokens := current_tokens + (LENGTH(entry_record.summary) / 4);
    END LOOP;
    
    RETURN context_text;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Accounts 相关表（团队/组织管理）
-- ============================================================================

-- 账户角色枚举类型
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_role') THEN
        CREATE TYPE account_role AS ENUM ('owner', 'member');
    END IF;
END$$;

-- 账户表（支持个人账户和团队账户）
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 主要拥有者（不能被移除，除非转移所有权）
    primary_owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- 账户名称
    name VARCHAR(255),
    -- 账户slug（用于URL）
    slug VARCHAR(255) UNIQUE,
    -- 是否为个人账户
    personal_account BOOLEAN DEFAULT false NOT NULL,
    -- 元数据
    public_metadata JSONB DEFAULT '{}'::jsonb,
    private_metadata JSONB DEFAULT '{}'::jsonb,
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 约束：个人账户可以没有slug，团队账户必须有slug
ALTER TABLE accounts
    ADD CONSTRAINT accounts_slug_null_if_personal_account_true CHECK (
        (personal_account = true AND slug is null)
        OR (personal_account = false AND slug is not null)
    );

-- 索引
CREATE INDEX IF NOT EXISTS idx_accounts_primary_owner ON accounts(primary_owner_user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_slug ON accounts(slug) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_accounts_created_at ON accounts(created_at);

-- 账户成员表
CREATE TABLE IF NOT EXISTS account_user (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    account_role account_role NOT NULL DEFAULT 'member',
    PRIMARY KEY (user_id, account_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_account_user_account ON account_user(account_id);
CREATE INDEX IF NOT EXISTS idx_account_user_user ON account_user(user_id);

-- 触发器：slug自动转换为小写并替换特殊字符
CREATE OR REPLACE FUNCTION slugify_account_slug()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.slug IS NOT NULL THEN
        NEW.slug = lower(regexp_replace(NEW.slug, '[^a-zA-Z0-9-]+', '-', 'g'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_slugify_account_slug ON accounts;
CREATE TRIGGER trigger_slugify_account_slug
    BEFORE INSERT OR UPDATE ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION slugify_account_slug();

-- 触发器：更新 updated_at
DROP TRIGGER IF EXISTS update_accounts_updated_at ON accounts;
CREATE TRIGGER update_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 触发器：创建账户时自动添加创建者为owner
CREATE OR REPLACE FUNCTION add_creator_to_account()
RETURNS TRIGGER AS $$
BEGIN
    -- 将创建者添加为账户的owner
    INSERT INTO account_user (account_id, user_id, account_role)
    VALUES (NEW.id, NEW.primary_owner_user_id, 'owner')
    ON CONFLICT (user_id, account_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_add_creator_to_account ON accounts;
CREATE TRIGGER trigger_add_creator_to_account
    AFTER INSERT ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION add_creator_to_account();

-- 触发器：用户注册时自动创建个人账户
CREATE OR REPLACE FUNCTION create_personal_account_for_user()
RETURNS TRIGGER AS $$
DECLARE
    generated_name TEXT;
BEGIN
    -- 从email生成用户名
    IF NEW.email IS NOT NULL THEN
        generated_name := split_part(NEW.email, '@', 1);
    ELSE
        generated_name := 'User';
    END IF;
    
    -- 创建个人账户（ID与用户ID相同）
    INSERT INTO accounts (id, name, primary_owner_user_id, personal_account)
    VALUES (NEW.id, generated_name, NEW.id, true)
    ON CONFLICT (id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_create_personal_account ON users;
CREATE TRIGGER trigger_create_personal_account
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_personal_account_for_user();
