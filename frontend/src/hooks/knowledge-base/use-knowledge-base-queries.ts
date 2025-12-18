import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useAuth } from '@/components/AuthProvider';
import { knowledgeBaseKeys } from './keys';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

// Only keep the types that are actually used
export interface KnowledgeBaseEntry {
  entry_id: string;
  name: string;
  description?: string;
  content: string;
  usage_context: 'always' | 'on_request' | 'contextual';
  is_active: boolean;
  content_tokens?: number;
  created_at: string;
  updated_at: string;
}

export interface UpdateKnowledgeBaseEntryRequest {
  name?: string;
  description?: string;
  content?: string;
  usage_context?: 'always' | 'on_request' | 'contextual';
  is_active?: boolean;
}


export function useKnowledgeBaseEntry(entryId: string) {
  const { token } = useAuth();
  
  return useQuery({
    queryKey: knowledgeBaseKeys.entry(entryId),
    queryFn: async (): Promise<KnowledgeBaseEntry> => {
      if (!token) {
        throw new Error('No access token available');
      }
      
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      const response = await fetch(`${API_URL}/knowledge-base/${entryId}`, { headers });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to fetch knowledge base entry');
      }
      
      return await response.json();
    },
    enabled: !!entryId,
  });
}

export function useUpdateKnowledgeBaseEntry() {
  const queryClient = useQueryClient();
  const { token } = useAuth();
  
  return useMutation({
    mutationFn: async ({ entryId, data }: { entryId: string; data: UpdateKnowledgeBaseEntryRequest }) => {
      if (!token) {
        throw new Error('No access token available');
      }
      
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      const response = await fetch(`${API_URL}/knowledge-base/${entryId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to update knowledge base entry');
      }
      
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.all });
      toast.success('Knowledge base entry updated successfully');
    },
    onError: (error) => {
      toast.error(`Failed to update knowledge base entry: ${error.message}`);
    },
  });
}

export function useDeleteKnowledgeBaseEntry() {
  const queryClient = useQueryClient();
  const { token } = useAuth();
  
  return useMutation({
    mutationFn: async (entryId: string) => {
      if (!token) {
        throw new Error('No access token available');
      }
      
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      const response = await fetch(`${API_URL}/knowledge-base/${entryId}`, {
        method: 'DELETE',
        headers,
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete knowledge base entry');
      }
      
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.all });
      toast.success('Knowledge base entry deleted successfully');
    },
    onError: (error) => {
      toast.error(`Failed to delete knowledge base entry: ${error.message}`);
    },
  });
}


export function useAgentKnowledgeBaseContext(agentId: string, maxTokens = 4000) {
  const { token } = useAuth();
  
  return useQuery({
    queryKey: knowledgeBaseKeys.agentContext(agentId),
    queryFn: async () => {
      if (!token) {
        throw new Error('No access token available');
      }
      
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      const url = new URL(`${API_URL}/knowledge-base/agents/${agentId}/context`);
      url.searchParams.set('max_tokens', maxTokens.toString());
      
      const response = await fetch(url.toString(), { headers });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to fetch agent knowledge base context');
      }
      
      return await response.json();
    },
    enabled: !!agentId,
  });
}

