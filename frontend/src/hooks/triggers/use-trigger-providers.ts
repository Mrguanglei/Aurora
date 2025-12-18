import { useQuery } from '@tanstack/react-query';
import { TriggerProvider } from '@/components/agents/triggers/types';
import { useAuth } from '@/components/AuthProvider';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

const fetchTriggerProviders = async (token: string | null): Promise<TriggerProvider[]> => {
  if (!token) {
    throw new Error('You must be logged in to create a trigger');
  }
  
  const response = await fetch(`${API_URL}/triggers/providers`, {
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch trigger providers');
  }
  return response.json();
};

export const useTriggerProviders = () => {
  const { token } = useAuth();
  
  return useQuery({
    queryKey: ['trigger-providers'],
    queryFn: () => fetchTriggerProviders(token),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}; 