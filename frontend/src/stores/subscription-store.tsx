// Stub file - billing system removed
import React from 'react';

export const useSharedSubscription = () => {
  return {
    subscription: null,
    isLoading: false,
  };
};

export const SubscriptionStoreSync = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};
