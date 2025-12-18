// Note: Phone verification has been removed as part of Supabase migration to private deployment
// This service is kept for API compatibility but returns mock responses



export interface FactorInfo {
  id: string;
  friendly_name?: string;
  factor_type?: string;
  status?: string;
  phone?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PhoneVerificationEnroll {
  friendly_name: string;
  phone_number: string;
}

export interface PhoneVerificationChallenge {
  factor_id: string;
}

export interface PhoneVerificationVerify {
  factor_id: string;
  challenge_id: string;
  code: string;
}

export interface PhoneVerificationChallengeAndVerify {
  factor_id: string;
  code: string;
}

export interface PhoneVerificationResponse {
  success: boolean;
  message?: string;
  id?: string;
  expires_at?: string;
}

export interface EnrollFactorResponse {
  id: string;
  friendly_name: string;
  phone_number: string;
  qr_code?: string;
  secret?: string;
}

export interface ChallengeResponse {
  id: string;
  expires_at?: string;
}

export interface ListFactorsResponse {
  factors: FactorInfo[];
}

export interface AALResponse {
  current_level?: string;
  next_level?: string;
  current_authentication_methods?: string[];
  // Add action guidance based on AAL status
  action_required?: string;
  message?: string;
  // Phone verification requirement fields
  phone_verification_required?: boolean;
  user_created_at?: string;
  cutoff_date?: string;
  // Computed verification status fields (same as PhoneVerificationStatus)
  verification_required?: boolean;
  is_verified?: boolean;
  factors?: FactorInfo[];
}




export const phoneVerificationService = {
  /**
   * Enroll phone number for SMS-based 2FA
   */
  async enrollPhoneNumber(data: PhoneVerificationEnroll): Promise<EnrollFactorResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * Create a challenge for an enrolled phone factor (sends SMS)
   */
  async createChallenge(data: PhoneVerificationChallenge): Promise<ChallengeResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * Verify SMS code for phone verification
   */
  async verifyChallenge(data: PhoneVerificationVerify): Promise<PhoneVerificationResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * Create challenge and verify in one step
   */
  async challengeAndVerify(data: PhoneVerificationChallengeAndVerify): Promise<PhoneVerificationResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * Resend SMS code (create new challenge for existing factor)
   */
  async resendSMS(factorId: string): Promise<ChallengeResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * List all enrolled MFA factors
   */
  async listFactors(): Promise<ListFactorsResponse> {
    return { factors: [] };
  },

  /**
   * Remove phone verification from account
   */
  async unenrollFactor(factorId: string): Promise<PhoneVerificationResponse> {
    throw new Error('Phone verification not available in private deployment');
  },

  /**
   * Get Authenticator Assurance Level
   */
  async getAAL(): Promise<AALResponse> {
    return {
      current_level: 'aal1',
      next_level: 'aal1',
      current_authentication_methods: ['password'],
      phone_verification_required: false,
      verification_required: false,
      is_verified: true,
      factors: []
    };
  }
};