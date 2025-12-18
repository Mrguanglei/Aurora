'use client';

import { FormEvent, useState } from 'react';
import { signInWithPassword, signUpWithPassword } from '@/app/auth/actions';
import { SubmitButton } from '@/components/ui/submit-button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useTranslations } from 'next-intl';
import { isElectron, getAuthOrigin } from '@/lib/utils/is-electron';

interface PasswordSignInProps {
  isSignUp?: boolean;
  returnUrl?: string;
  onSwitchMode?: () => void;
}

export default function PasswordSignIn({ 
  isSignUp = false, 
  returnUrl, 
  onSwitchMode 
}: PasswordSignInProps) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const t = useTranslations('auth');
  const [email, setEmail] = useState('');

  const handlePasswordAuth = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);
    formData.append('confirmPassword', confirmPassword);
    formData.append('returnUrl', returnUrl || '/dashboard');
    formData.append('origin', isElectron() ? getAuthOrigin() : window.location.origin);
    
    try {
      if (isSignUp) {
        if (!acceptedTerms) {
          toast.error(t('pleaseAcceptTerms') || 'Please accept the terms');
          return;
        }
        formData.append('acceptedTerms', 'true');
        const result = await signUpWithPassword({}, formData);
        if (result && typeof result === 'object' && 'message' in result) {
          toast.error(result.message as string);
        }
      } else {
        const result = await signInWithPassword({}, formData);
        if (result && typeof result === 'object' && 'message' in result) {
          toast.error(result.message as string);
        }
      }
    } catch (error: any) {
      // redirect() throws an exception, which is expected behavior
      // Only show error for actual exceptions
      if (error.message && !error.message.includes('NEXT_REDIRECT')) {
        toast.error(error.message || 'Authentication failed');
      }
    }
  };

  return (
    <form className="space-y-4" onSubmit={handlePasswordAuth}>
      <Input
        id="email"
        name="email"
        type="email"
        placeholder={t('emailAddress') || 'Email address'}
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <Input
        id="password"
        name="password"
        type="password"
        placeholder={t('password') || 'Password'}
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      {isSignUp && (
        <Input
          id="confirmPassword"
          name="confirmPassword"
          type="password"
          placeholder={t('confirmPassword') || 'Confirm password'}
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
      )}

      {isSignUp && (
        <div className="flex items-center gap-2">
          <Checkbox
            id="gdprConsent"
            checked={acceptedTerms}
            onCheckedChange={(checked) => setAcceptedTerms(checked === true)}
            required
            className="h-5 w-5"
          />
          <label 
            htmlFor="gdprConsent" 
            className="text-xs text-muted-foreground leading-relaxed cursor-pointer select-none flex-1"
          >
            {t.rich('acceptPrivacyTerms', {
              privacyPolicy: (chunks) => (
                <a 
                  href="" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline underline-offset-2 text-primary"
                  onClick={(e) => e.stopPropagation()}
                >
                  {chunks}
                </a>
              ),
              termsOfService: (chunks) => (
                <a 
                  href=""
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline underline-offset-2 text-primary"
                  onClick={(e) => e.stopPropagation()}
                >
                  {chunks}
                </a>
              )
            })}
          </label>
        </div>
      )}

      <button
        type="submit"
        disabled={isSignUp ? !acceptedTerms || !email || !password || password !== confirmPassword : !email || !password}
        className="w-full h-10 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSignUp ? (t('signUp') || 'Sign Up') : (t('signIn') || 'Sign In')}
      </button>

      {onSwitchMode && (
        <Button 
          type="button" 
          variant="ghost" 
          className="w-full text-sm"
          onClick={onSwitchMode}
        >
          {isSignUp 
            ? (t('alreadyHaveAccount') || 'Already have an account? Sign in') 
            : (t('dontHaveAccount') || "Don't have an account? Sign up")}
        </Button>
      )}
    </form>
  );
}
