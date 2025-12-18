'use client';

import { toast } from 'sonner';
import { Icons } from './home/icons';
import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';

interface GoogleSignInProps {
  returnUrl?: string;
  referralCode?: string;
}

export default function GoogleSignIn({ returnUrl, referralCode }: GoogleSignInProps) {
  const t = useTranslations('auth');

  const handleGoogleSignIn = () => {
    // Supabase OAuth移除 - Google登录已禁用
    toast.error('Google sign-in is not available in this version');
  };

  return (
    <Button
      onClick={handleGoogleSignIn}
      disabled={true}
      variant="outline"
      size="lg"
      className="w-full h-12 opacity-50 cursor-not-allowed"
      type="button"
    >
      <Icons.google className="w-4 h-4" />
      <span>{t('continueWithGoogle')} (Disabled)</span>
    </Button>
  );
}