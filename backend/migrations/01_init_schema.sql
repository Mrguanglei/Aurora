-- ============================================================================
-- Aurora Private Deployment - Database Schema Migration
-- ============================================================================
-- 优化后的数据库架构迁移脚本
-- 顺序：枚举类型 -> 函数 -> 表创建 -> 外键约束 -> 索引 -> 触发器

-- ============================================================================
-- 1. 创建枚举类型
-- ============================================================================

-- 用户角色枚举
DO $$ BEGIN
    CREATE TYPE account_role AS ENUM ('owner', 'admin', 'member');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 记忆类型枚举
DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('fact', 'event', 'preference', 'skill', 'relationship', 'context', 'conversation_summary');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 记忆提取状态枚举
DO $$ BEGIN
    CREATE TYPE memory_extraction_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Agent触发器类型枚举
DO $$ BEGIN
    CREATE TYPE agent_trigger_type AS ENUM ('telegram', 'slack', 'webhook', 'schedule', 'email', 'github', 'discord', 'teams', 'api');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- 2. 创建辅助函数
-- ============================================================================

-- 更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 获取用户记忆启用状态函数
CREATE OR REPLACE FUNCTION get_user_memory_enabled(p_account_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(
        (SELECT memory_enabled FROM accounts WHERE id = p_account_id),
        TRUE
    );
END;
$$ LANGUAGE plpgsql;

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

-- 触发器：创建账户时自动添加创建者为owner
CREATE OR REPLACE FUNCTION add_creator_to_account()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO account_user (account_id, user_id, account_role)
    VALUES (NEW.id, NEW.primary_owner_user_id, 'owner')
    ON CONFLICT (user_id, account_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- ============================================================================
-- 3. 创建所有表（按依赖顺序）
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
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT FALSE,
    avatar_url TEXT
);

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    personal_account BOOLEAN DEFAULT false NOT NULL,
    memory_enabled BOOLEAN DEFAULT TRUE,
    public_metadata JSONB DEFAULT '{}'::jsonb,
    private_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 账户成员表
CREATE TABLE IF NOT EXISTS account_user (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    account_role account_role NOT NULL DEFAULT 'member',
    PRIMARY KEY (user_id, account_id)
);

-- 用户角色表
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, role)
);

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_public BOOLEAN DEFAULT false,
    icon_name TEXT,
    description TEXT,
    sandbox JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent表
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
    is_public BOOLEAN DEFAULT false,
    marketplace_published_at TIMESTAMP WITH TIME ZONE,
    download_count INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

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
    created_by UUID REFERENCES accounts(id),
    change_description TEXT,
    previous_version_id UUID REFERENCES agent_versions(version_id),
    UNIQUE(agent_id, version_number),
    UNIQUE(agent_id, version_name)
);

-- Agent版本历史表
CREATE TABLE IF NOT EXISTS agent_version_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES agent_versions(version_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    performed_by UUID REFERENCES accounts(id) ON DELETE SET NULL,
    change_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    memory_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50),
    type TEXT NOT NULL DEFAULT 'text',
    is_llm_message BOOLEAN DEFAULT TRUE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent模板表
CREATE TABLE IF NOT EXISTS agent_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    mcp_requirements JSONB DEFAULT '[]'::jsonb,
    agentpress_tools JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}'::text[],
    is_public BOOLEAN DEFAULT false,
    marketplace_published_at TIMESTAMP WITH TIME ZONE,
    download_count INTEGER DEFAULT 0,
    avatar VARCHAR(10),
    avatar_color VARCHAR(7),
    metadata JSONB DEFAULT '{}'::jsonb,
    icon_name VARCHAR(255),
    icon_color VARCHAR(255),
    icon_background VARCHAR(255),
    is_kortix_team BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 工具调用表
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Agent运行记录表
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    agent_version_id UUID REFERENCES agent_versions(version_id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户在线状态会话表
CREATE TABLE IF NOT EXISTS user_presence_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES threads(thread_id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 用户记忆表
CREATE TABLE IF NOT EXISTS user_memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    memory_type memory_type NOT NULL DEFAULT 'fact',
    source_thread_id UUID REFERENCES threads(thread_id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.8,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 记忆提取队列表
CREATE TABLE IF NOT EXISTS memory_extraction_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_ids JSONB NOT NULL DEFAULT '[]',
    status memory_extraction_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

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

-- Agent触发器表
CREATE TABLE IF NOT EXISTS agent_triggers (
    trigger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    trigger_type agent_trigger_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 触发器事件日志表
CREATE TABLE IF NOT EXISTS trigger_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_id UUID NOT NULL REFERENCES agent_triggers(trigger_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    trigger_type agent_trigger_type NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    should_execute_agent BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 自定义触发器提供商表
CREATE TABLE IF NOT EXISTS custom_trigger_providers (
    provider_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    provider_class TEXT,
    config_schema JSONB DEFAULT '{}'::jsonb,
    webhook_enabled BOOLEAN DEFAULT FALSE,
    webhook_config JSONB,
    response_template JSONB,
    field_mappings JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES accounts(id)
);

-- OAuth安装表
CREATE TABLE IF NOT EXISTS oauth_installations (
    installation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_id UUID NOT NULL REFERENCES agent_triggers(trigger_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_in INTEGER,
    scope TEXT,
    provider_data JSONB DEFAULT '{}'::jsonb,
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

-- ============================================================================
-- 3.x. 创建 basejump schema 兼容层（本地部署使用）
-- ============================================================================

-- 创建 basejump schema（如果不存在）
CREATE SCHEMA IF NOT EXISTS basejump;

-- 创建 auth schema（必须在创建函数之前）
CREATE SCHEMA IF NOT EXISTS auth;

-- 创建 auth.uid() 函数（本地部署模拟）
-- 注意：这个函数返回 NULL，因为本地部署通常不使用 RLS
-- 如果需要 RLS 支持，需要配置 set_config 来设置当前用户
CREATE OR REPLACE FUNCTION auth.uid()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT NULLIF(current_setting('request.jwt.claim.sub', TRUE), '')::UUID;
$$;

-- 为 accounts 表创建视图（basejump.accounts -> public.accounts）
CREATE OR REPLACE VIEW basejump.accounts AS SELECT * FROM public.accounts;

-- 为 account_user 表创建视图（basejump.account_user -> public.account_user）
CREATE OR REPLACE VIEW basejump.account_user AS SELECT * FROM public.account_user;

-- 创建 has_role_on_account 函数（兼容 Supabase 的 RLS 策略）
-- 这个函数检查当前用户是否在指定账户中拥有指定角色
CREATE OR REPLACE FUNCTION basejump.has_role_on_account(
    account_id UUID,
    passed_in_role TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.account_user au
        WHERE au.account_id = has_role_on_account.account_id
          AND au.user_id = auth.uid()
          AND (
              passed_in_role IS NULL
              OR au.account_role::TEXT = passed_in_role
          )
    );
$$;

-- 添加注释
COMMENT ON SCHEMA basejump IS 'Compatibility schema for Supabase basejump functions and views (local deployment)';
COMMENT ON SCHEMA auth IS 'Authentication schema for Supabase compatibility (local deployment)';
COMMENT ON FUNCTION basejump.has_role_on_account IS 'Check if current user has a role on the specified account (Supabase compatibility)';
COMMENT ON FUNCTION auth.uid IS 'Get current authenticated user ID from JWT claim (Supabase compatibility)';

-- 用户反馈表
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating DECIMAL(2,1) NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0 AND rating % 0.5 = 0),
    feedback_text TEXT,
    help_improve BOOLEAN DEFAULT TRUE,
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- ============================================================================
-- 4. 添加外键约束（需要在相关表创建后）
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
-- 5. 创建所有索引
-- ============================================================================

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- 账户表索引
CREATE INDEX IF NOT EXISTS idx_accounts_primary_owner ON accounts(primary_owner_user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_slug ON accounts(slug) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_accounts_created_at ON accounts(created_at);

-- 账户成员表索引
CREATE INDEX IF NOT EXISTS idx_account_user_account ON account_user(account_id);
CREATE INDEX IF NOT EXISTS idx_account_user_user ON account_user(user_id);

-- 项目表索引
CREATE INDEX IF NOT EXISTS idx_projects_account_id ON projects(account_id);
CREATE INDEX IF NOT EXISTS idx_projects_is_public ON projects(is_public);

-- Agent表索引
CREATE INDEX IF NOT EXISTS idx_agents_account_id ON agents(account_id);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at);
CREATE INDEX IF NOT EXISTS idx_agents_is_default ON agents(account_id, is_default) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_agents_current_version ON agents(current_version_id);
CREATE INDEX IF NOT EXISTS idx_agents_is_public ON agents(is_public);
CREATE INDEX IF NOT EXISTS idx_agents_marketplace_published_at ON agents(marketplace_published_at);
CREATE INDEX IF NOT EXISTS idx_agents_download_count ON agents(download_count);
CREATE INDEX IF NOT EXISTS idx_agents_tags ON agents USING gin(tags);

-- Agent版本表索引
CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_id ON agent_versions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_versions_is_active ON agent_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_versions_version_number ON agent_versions(version_number);
CREATE INDEX IF NOT EXISTS idx_agent_versions_previous_version_id ON agent_versions(previous_version_id);

-- Agent版本历史表索引
CREATE INDEX IF NOT EXISTS idx_agent_version_history_agent_id ON agent_version_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_version_history_version_id ON agent_version_history(version_id);

-- Threads表索引
CREATE INDEX IF NOT EXISTS idx_threads_account_id ON threads(account_id);
CREATE INDEX IF NOT EXISTS idx_threads_project_id ON threads(project_id);
CREATE INDEX IF NOT EXISTS idx_threads_agent_id ON threads(agent_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);
CREATE INDEX IF NOT EXISTS idx_threads_memory_enabled ON threads(thread_id) WHERE memory_enabled = FALSE;

-- Messages表索引
CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_type_created_desc ON messages(thread_id, type, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_created_desc ON messages(thread_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_llm_created ON messages(thread_id, created_at) WHERE is_llm_message = TRUE;

-- Agent Templates表索引
CREATE INDEX IF NOT EXISTS idx_agent_templates_creator_created_desc ON agent_templates(creator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_templates_is_public ON agent_templates(is_public);
CREATE INDEX IF NOT EXISTS idx_agent_templates_marketplace_published_at ON agent_templates(marketplace_published_at);

-- 工具调用表索引
CREATE INDEX IF NOT EXISTS idx_tool_calls_thread_id ON tool_calls(thread_id);

-- Agent运行记录表索引
CREATE INDEX IF NOT EXISTS idx_agent_runs_thread_id ON agent_runs(thread_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at);

-- 用户在线状态会话表索引
CREATE INDEX IF NOT EXISTS idx_presence_user_id ON user_presence_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_presence_thread_id ON user_presence_sessions(thread_id);

-- API密钥表索引
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- 用户记忆表索引
CREATE INDEX IF NOT EXISTS idx_user_memories_account_id ON user_memories(account_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_memory_type ON user_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_created_at ON user_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_memories_source_thread ON user_memories(source_thread_id) WHERE source_thread_id IS NOT NULL;

-- 记忆提取队列表索引
CREATE INDEX IF NOT EXISTS idx_memory_queue_account_id ON memory_extraction_queue(account_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_thread_id ON memory_extraction_queue(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_status ON memory_extraction_queue(status) WHERE status IN ('pending', 'processing');

-- 知识库文件夹表索引
CREATE INDEX IF NOT EXISTS idx_kb_folders_account_id ON knowledge_base_folders(account_id);

-- 知识库条目表索引
CREATE INDEX IF NOT EXISTS idx_kb_entries_folder_id ON knowledge_base_entries(folder_id);
CREATE INDEX IF NOT EXISTS idx_kb_entries_account_id ON knowledge_base_entries(account_id);

-- Agent知识库分配表索引
CREATE INDEX IF NOT EXISTS idx_kb_entry_assignments_agent_id ON agent_knowledge_entry_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_kb_entry_assignments_entry_id ON agent_knowledge_entry_assignments(entry_id);

-- Agent触发器表索引
CREATE INDEX IF NOT EXISTS idx_agent_triggers_agent_id ON agent_triggers(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_triggers_trigger_type ON agent_triggers(trigger_type);
CREATE INDEX IF NOT EXISTS idx_agent_triggers_is_active ON agent_triggers(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_triggers_created_at ON agent_triggers(created_at);

-- 触发器事件日志表索引
CREATE INDEX IF NOT EXISTS idx_trigger_events_trigger_id ON trigger_events(trigger_id);
CREATE INDEX IF NOT EXISTS idx_trigger_events_agent_id ON trigger_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_trigger_events_timestamp ON trigger_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_trigger_events_success ON trigger_events(success);

-- 自定义触发器提供商表索引
CREATE INDEX IF NOT EXISTS idx_custom_trigger_providers_trigger_type ON custom_trigger_providers(trigger_type);
CREATE INDEX IF NOT EXISTS idx_custom_trigger_providers_is_active ON custom_trigger_providers(is_active);

-- OAuth安装表索引
CREATE INDEX IF NOT EXISTS idx_oauth_installations_trigger_id ON oauth_installations(trigger_id);
CREATE INDEX IF NOT EXISTS idx_oauth_installations_provider ON oauth_installations(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_installations_installed_at ON oauth_installations(installed_at);

-- 用户MCP凭证配置表索引
CREATE INDEX IF NOT EXISTS idx_credential_profiles_account_mcp ON user_mcp_credential_profiles(account_id, mcp_qualified_name);
CREATE INDEX IF NOT EXISTS idx_credential_profiles_account_active ON user_mcp_credential_profiles(account_id, is_active) WHERE is_active = true;

-- 用户反馈表索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_unique
    ON feedback(thread_id, message_id, account_id)
    WHERE thread_id IS NOT NULL AND message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_thread_id ON feedback(thread_id);
CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_feedback_account_id ON feedback(account_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);

-- ============================================================================
-- 6. 创建所有触发器
-- ============================================================================

-- 用户表触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_create_personal_account ON users;
CREATE TRIGGER trigger_create_personal_account
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_personal_account_for_user();

-- 账户表触发器
DROP TRIGGER IF EXISTS update_accounts_updated_at ON accounts;
CREATE TRIGGER update_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_add_creator_to_account ON accounts;
CREATE TRIGGER trigger_add_creator_to_account
    AFTER INSERT ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION add_creator_to_account();

-- 项目表触发器
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON COLUMN projects.sandbox IS 'Sandbox metadata including id, password, VNC URL, and website URL';
COMMENT ON COLUMN projects.description IS 'Project description';

-- Agent表触发器
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Agent版本表触发器
DROP TRIGGER IF EXISTS update_agent_versions_updated_at ON agent_versions;
CREATE TRIGGER update_agent_versions_updated_at BEFORE UPDATE ON agent_versions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Threads表触发器
DROP TRIGGER IF EXISTS update_threads_updated_at ON threads;
CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Messages表触发器
DROP TRIGGER IF EXISTS update_messages_updated_at ON messages;
CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Agent Templates表触发器
DROP TRIGGER IF EXISTS update_agent_templates_updated_at ON agent_templates;
CREATE TRIGGER update_agent_templates_updated_at BEFORE UPDATE ON agent_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- User Presence Sessions表触发器
DROP TRIGGER IF EXISTS update_presence_updated_at ON user_presence_sessions;
CREATE TRIGGER update_presence_updated_at BEFORE UPDATE ON user_presence_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- User Memories表触发器
DROP TRIGGER IF EXISTS update_user_memories_updated_at ON user_memories;
CREATE TRIGGER update_user_memories_updated_at BEFORE UPDATE ON user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Knowledge Base Folders表触发器
DROP TRIGGER IF EXISTS update_kb_folders_updated_at ON knowledge_base_folders;
CREATE TRIGGER update_kb_folders_updated_at BEFORE UPDATE ON knowledge_base_folders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Knowledge Base Entries表触发器
DROP TRIGGER IF EXISTS update_kb_entries_updated_at ON knowledge_base_entries;
CREATE TRIGGER update_kb_entries_updated_at BEFORE UPDATE ON knowledge_base_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Agent Triggers表触发器
DROP TRIGGER IF EXISTS update_agent_triggers_updated_at ON agent_triggers;
CREATE TRIGGER update_agent_triggers_updated_at BEFORE UPDATE ON agent_triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Custom Trigger Providers表触发器
DROP TRIGGER IF EXISTS update_custom_trigger_providers_updated_at ON custom_trigger_providers;
CREATE TRIGGER update_custom_trigger_providers_updated_at BEFORE UPDATE ON custom_trigger_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- OAuth Installations表触发器
DROP TRIGGER IF EXISTS update_oauth_installations_updated_at ON oauth_installations;
CREATE TRIGGER update_oauth_installations_updated_at BEFORE UPDATE ON oauth_installations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- User MCP Credential Profiles表触发器
DROP TRIGGER IF EXISTS update_credential_profiles_updated_at ON user_mcp_credential_profiles;
CREATE TRIGGER update_credential_profiles_updated_at BEFORE UPDATE ON user_mcp_credential_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- User Feedback表触发器
CREATE OR REPLACE FUNCTION update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_feedback_updated_at ON feedback;
CREATE TRIGGER update_feedback_updated_at
    BEFORE UPDATE ON feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_feedback_updated_at();

-- Comments
COMMENT ON TABLE feedback IS 'Stores user feedback (ratings and comments). Can be associated with messages/threads or standalone.';
COMMENT ON COLUMN feedback.rating IS 'Rating from 0.5 to 5.0 in 0.5 increments (half stars)';
COMMENT ON COLUMN feedback.feedback_text IS 'Optional text feedback from the user';
COMMENT ON COLUMN feedback.help_improve IS 'Whether the user wants to help improve the service';
COMMENT ON COLUMN feedback.context IS 'Additional context/metadata as JSONB';
COMMENT ON COLUMN feedback.thread_id IS 'Optional thread ID if feedback is associated with a thread';
COMMENT ON COLUMN feedback.message_id IS 'Optional message ID if feedback is associated with a message';

-- ============================================================================
-- 迁移完成
-- ============================================================================