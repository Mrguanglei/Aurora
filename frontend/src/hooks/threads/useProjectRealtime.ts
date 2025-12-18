'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { threadKeys } from '@/hooks/threads/keys';
import { Project } from '@/lib/api/threads';

/**
 * Hook to subscribe to real-time project updates and invalidate React Query cache
 * This ensures the frontend immediately knows when sandbox data is updated
 * 
 * Note: Real-time subscriptions have been removed as part of Supabase migration.
 * The system now uses polling via React Query's refetchInterval instead.
 */
export function useProjectRealtime(projectId?: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!projectId) return;

    // Real-time subscription disabled - using polling instead
    console.log(`[Project Realtime] Real-time subscription disabled for project ${projectId}`);
    console.log('[Project Realtime] Using polling-based updates instead');
  }, [projectId, queryClient]);
}
