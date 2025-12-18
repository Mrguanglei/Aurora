/**
 * 账单 API 已删除（私有化部署）
 * 本文件保留用于向后兼容性
 */

export interface AccountState {
  is_trial: boolean;
  trial_end_date: string | null;
  is_locked: boolean;
  credits: number;
  monthly_credits: number;
}

export const billingApi = {
  getAccountState: async () => ({
    is_trial: false,
    trial_end_date: null,
    is_locked: false,
    credits: 999999,
    monthly_credits: 999999,
  }),
};

export const createCheckoutSession = async () => null;

export interface CreateCheckoutSessionRequest {
  priceId: string;
}

export interface CreateCheckoutSessionResponse {
  url: string;
}
