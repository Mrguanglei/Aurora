-- 修复记忆相关表的创建，使用正确的表引用
CREATE EXTENSION IF NOT EXISTS vector;

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

-- 创建user_memories表
CREATE TABLE IF NOT EXISTS user_memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    memory_type memory_type NOT NULL DEFAULT 'fact',
    embedding vector(1536),
    source_thread_id UUID REFERENCES threads(thread_id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.8,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 创建memory_extraction_queue表
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_memories_account_id ON user_memories(account_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_memory_type ON user_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_created_at ON user_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_memories_source_thread ON user_memories(source_thread_id) WHERE source_thread_id IS NOT NULL;

-- 只有在支持vector的情况下创建向量索引
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_user_memories_embedding_vector ON user_memories 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
EXCEPTION
    WHEN undefined_function THEN null;
END $$;

CREATE INDEX IF NOT EXISTS idx_memory_queue_account_id ON memory_extraction_queue(account_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_thread_id ON memory_extraction_queue(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_queue_status ON memory_extraction_queue(status) WHERE status IN ('pending', 'processing');
