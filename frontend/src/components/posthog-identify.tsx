'use client';

import posthog from 'posthog-js';
import { useEffect } from 'react';
import { useAuth } from '@/components/AuthProvider';

export const PostHogIdentify = () => {
  const { user } = useAuth();
  
  useEffect(() => {
    if (user) {
      posthog.identify(user.id, { email: user.email });
    } else {
      posthog.reset();
    }
  }, [user]);

  return null;
};
