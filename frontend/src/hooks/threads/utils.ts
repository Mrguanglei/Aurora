import { backendApi } from "@/lib/api-client";
import { getProject, updateProject, type Project } from "@/lib/api/threads";

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

// Re-export Project type for consistent imports
export type { Project };

export type Thread = {
    thread_id: string;
    project_id?: string | null;
    is_public?: boolean;
    created_at: string;
    updated_at: string;
    metadata?: {
      agent_id?: string;
    
      [key: string]: any;
    };
    [key: string]: any;
  };
  

  export const getThread = async (threadId: string, token?: string | null): Promise<Thread> => {
    // Build headers with optional auth token
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Use backend API endpoint with auth handling
    const response = await fetch(`${API_URL}/threads/${threadId}`, {
      headers,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(errorText || `Failed to fetch thread: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  };

export const updateThread = async (
    threadId: string,
    data: Partial<Thread>,
    token?: string | null,
  ): Promise<Thread> => {
    if (!token) {
      throw new Error('You must be logged in to update a thread');
    }

    // Use backend API endpoint with auth handling
    const response = await fetch(`${API_URL}/threads/${threadId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
      cache: 'no-store',
    });
  
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      console.error('Error updating thread:', errorText);
      throw new Error(`Error updating thread: ${errorText}`);
    }
  
    const updatedThread = await response.json();
    return updatedThread;
  };

export const toggleThreadPublicStatus = async (
    threadId: string,
    isPublic: boolean,
    token?: string | null,
  ): Promise<Thread> => {
    return updateThread(threadId, { is_public: isPublic }, token);
};

/**
 * Delete a thread using the backend API endpoint.
 * The backend handles deleting all associated data (messages, agent runs, project, sandbox).
 */
export const deleteThread = async (threadId: string, sandboxId?: string, token?: string | null): Promise<void> => {
    try {
      // Get auth token from localStorage if not provided
      let authToken = token;
      if (!authToken && typeof window !== 'undefined') {
        try {
          const authData = localStorage.getItem('auth-token');
          if (authData) {
            const parsed = JSON.parse(authData);
            authToken = parsed?.access_token || null;
          }
        } catch {
          // Ignore errors
        }
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      } else {
        console.warn('⚠️ No auth token found for deleteThread request');
      }

      // Use the backend DELETE endpoint which handles everything
      const response = await fetch(`${API_URL}/threads/${threadId}`, {
        method: 'DELETE',
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        console.error('Error deleting thread:', errorText);
        throw new Error(`Failed to delete thread: ${errorText}`);
      }

      console.log(`Thread ${threadId} deleted successfully`);
    } catch (error) {
      console.error('Error deleting thread:', error);
      throw error;
    }
  };
  

export const getPublicProjects = async (): Promise<Project[]> => {
    // NOTE: This function should not be called directly anymore
    // Use usePublicProjectsQuery() hook instead, which derives from cached threads
    // This is kept for backward compatibility but should be deprecated
    console.warn('getPublicProjects() called directly - use usePublicProjectsQuery() hook instead');
    
    try {
      const { getThreadsPaginated } = await import('@/lib/api/threads');
      const response = await getThreadsPaginated(undefined, 1, 20);

      if (!response?.threads) {
        return [];
      }

      const threads = response.threads;

      // Filter for public threads and extract unique projects
      const projectsMap = new Map<string, Project>();
      
      threads.forEach((thread: any) => {
        if (thread.is_public && thread.project_id && thread.project) {
          const project = thread.project;
          if (!projectsMap.has(project.project_id)) {
            projectsMap.set(project.project_id, {
              id: project.project_id,
              name: project.name || '',
              description: project.description || '',
              created_at: project.created_at,
              updated_at: project.updated_at,
              sandbox: project.sandbox || {
                id: '',
                pass: '',
                vnc_preview: '',
                sandbox_url: '',
              },
              is_public: true,
            });
          }
        }
      });

      return Array.from(projectsMap.values());
    } catch (err) {
      console.error('Error fetching public projects:', err);
      return [];
    }
  };



  // Re-export getProject and updateProject from threads.ts for backward compatibility
  // These are now properly implemented in threads.ts with React Query support
  export { getProject, updateProject };
