-- ============================================================================
-- 创建 basejump schema 兼容层
-- ============================================================================
-- 本地部署使用 public schema，而 Supabase 使用 basejump schema
-- 这个迁移创建兼容层，使得引用 basejump.account_user 的代码可以正常工作

BEGIN;

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

COMMIT;
