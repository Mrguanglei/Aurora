/**
 * 计费 / 订阅系统在自托管版本中已移除。
 * 本文件提供一组“固定返回值”的 Hook，用来兼容原有代码，
 * 确保在没有真实计费后端的情况下仍可正常构建和运行。
 *
 * 所有导出均为「空实现」：
 * - 不会调用任何外部计费服务
 * - 不会限制功能或下载
 * - 所有“升级 / 取消订阅 / 调整额度”等操作都是 no-op
 */

import { useCallback } from 'react';

// -------------------- 类型声明 --------------------

type AccountTier = {
  name?: string;
  tier_key?: string;
};

type AccountSubscription = {
  tier_key?: string;
};

export type AccountState = {
  plan: any;
  limits: any;
  tier?: AccountTier | null;
  subscription?: AccountSubscription | null;
  credits: {
    total: number;
    daily_refresh: {
      enabled: boolean;
      seconds_until_refresh: number | null;
    };
  };
};

// -------------------- 账户状态相关 --------------------

export const accountStateKeys = {
  accountState: ['accountState'] as const,
};

export const accountStateSelectors = {
  selectPlan: (state: any) => state?.plan ?? null,
  selectLimits: (state: any) => state?.limits ?? null,
  // 自托管环境下返回固定计划名称与高额度
  planName: (_state: any) => 'Local Plan',
  totalCredits: (_state: any) => 999999,
  tierKey: (_state: any) => 'free',
};

export function useAccountState(_options?: { enabled?: boolean }) {
  return {
    data: {
      plan: null,
      limits: {
        threads: {
          can_create: true,
          current: 0,
          max: 999999,
        },
        concurrent_runs: {
          running_count: 0,
          limit: 999999,
        },
        ai_worker_count: {
          current_count: 0,
          limit: 999999,
        },
        custom_mcp_count: {
          current_count: 0,
          limit: 999999,
        },
        trigger_count: {
          scheduled: {
            current_count: 0,
            limit: 999999,
          },
          app: {
            current_count: 0,
            limit: 999999,
          },
        },
      },
      tier: { name: 'Local Plan', tier_key: 'free' },
      subscription: null,
      credits: {
        total: 999999,
        daily_refresh: {
          enabled: false,
          seconds_until_refresh: null,
        },
      },
    },
    isLoading: false,
    error: null,
    refetch: async () => {},
  };
}

export async function invalidateAccountState(
  _queryClient?: any,
  _skipCache?: boolean,
  _force?: boolean,
) {
  // 自托管版本中不做任何事情，仅用于兼容旧代码
  return;
}

// -------------------- 下载限制相关 --------------------

export function useDownloadRestriction(_options?: { featureName?: string }) {
  const openUpgradeModal = useCallback(() => {
    // 自托管版本中不做任何事情，仅用于兼容旧代码
    return;
  }, []);

  return {
    canDownload: true,
    isRestricted: false,
    isPending: false,
    checkDownloadAllowed: () => true,
    reason: null as string | null,
    openUpgradeModal,
  };
}

// -------------------- 订阅 / 试用相关 --------------------

export function useTrialStatus(_options?: { enabled?: boolean }) {
  return {
    data: {
      hasTrial: false,
      trialDaysRemaining: 0,
      trialEndDate: null,
      trial_status: 'inactive' as 'active' | 'inactive' | 'expired',
      trial_ends_at: null as string | null,
    },
    isOnTrial: false,
    daysRemaining: 0,
    isLoading: false,
    error: null,
  };
}

export function useCancelTrial() {
  const mutateAsync = useCallback(async () => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

export function useCancelSubscription() {
  const mutateAsync = useCallback(async () => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

export function useCreatePortalSession() {
  const mutateAsync = useCallback(async () => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

export function useReactivateSubscription() {
  const mutateAsync = useCallback(async () => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

// -------------------- 线程 / 用户计费相关（含 admin） --------------------

export function useThreadBilling(_threadId?: string) {
  return {
    data: {
      cost: 0,
      currency: 'USD',
    },
    isLoading: false,
    error: null,
  };
}

export function useUserBillingSummary(_userId: string | null) {
  return {
    data: {
      totalCredits: 999999,
      usedCredits: 0,
      availableCredits: 999999,
      transactions: [],
    },
    isLoading: false,
    error: null,
    refetch: async () => {},
  };
}

export function useAdjustCredits() {
  const mutateAsync = useCallback(async (_data: any) => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

export function useProcessRefund() {
  const mutateAsync = useCallback(async (_data: any) => {
    return;
  }, []);
  return { mutateAsync, isPending: false };
}

export function useAdminUserTransactions(_userId: string | null) {
  return {
    data: [],
    isLoading: false,
    error: null,
    refetch: async () => {},
  };
}
