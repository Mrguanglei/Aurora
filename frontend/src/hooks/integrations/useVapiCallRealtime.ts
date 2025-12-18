'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface VapiCall {
  id: string;
  call_id: string;
  thread_id?: string;
  status: string;
  phone_number: string;
  duration_seconds?: number;
  transcript?: any;
  started_at?: string;
  ended_at?: string;
}

export function useVapiCallRealtime(callId?: string, threadId?: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!callId && !threadId) return;

    // Note: Real-time subscriptions have been removed as part of Supabase migration.
    // The system now uses polling via React Query's refetchInterval instead.
    // See MakeCallToolView and MonitorCallToolView for polling implementation.
    
    console.log(`[Vapi Realtime] Real-time subscription disabled for ${callId || threadId}`);
    console.log('[Vapi Realtime] Using polling-based updates instead');
  }, [callId, threadId, queryClient]);
}

