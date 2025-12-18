'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from 'react';
import { clearUserLocalStorage } from '@/lib/utils/clear-local-storage';

// Local auth types (replacing Supabase types)
type LocalUser = {
  id: string;
  email?: string;
  username?: string;
};

type LocalSession = {
  access_token: string;
  refresh_token?: string;
  user: LocalUser;
};

type AuthContextType = {
  session: LocalSession | null;
  user: LocalUser | null;
  token: string | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to get auth data from localStorage
function getStoredAuth(): LocalSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const authData = localStorage.getItem('auth-token');
    if (authData) {
      const parsed = JSON.parse(authData);
      if (parsed?.access_token) {
        // Decode JWT to get user info (basic decode, not verification)
        try {
          const payload = JSON.parse(atob(parsed.access_token.split('.')[1]));
          return {
            access_token: parsed.access_token,
            refresh_token: parsed.refresh_token,
            user: {
              id: payload.sub || payload.user_id || '',
              email: payload.email,
              username: payload.username,
            },
          };
        } catch {
          // Invalid token format
          return null;
        }
      }
    }
  } catch {
    // Ignore errors
  }
  return null;
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [session, setSession] = useState<LocalSession | null>(null);
  const [user, setUser] = useState<LocalUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for stored auth on mount
  useEffect(() => {
    const storedAuth = getStoredAuth();
    if (storedAuth) {
      setSession(storedAuth);
      setUser(storedAuth.user);
    }
        setIsLoading(false);
  }, []);

  // Listen for storage changes (e.g., login in another tab)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'auth-token') {
        const storedAuth = getStoredAuth();
        setSession(storedAuth);
        setUser(storedAuth?.user ?? null);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const signOut = useCallback(async () => {
    try {
      // Clear auth token from localStorage
      localStorage.removeItem('auth-token');
      setSession(null);
      setUser(null);
      // Clear other local storage
      clearUserLocalStorage();
      // Redirect to auth page
      window.location.href = '/auth';
    } catch (error) {
      console.error('❌ Error signing out:', error);
    }
  }, []);

  const value = {
    session,
    user,
    token: session?.access_token ?? null,
    isLoading,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
