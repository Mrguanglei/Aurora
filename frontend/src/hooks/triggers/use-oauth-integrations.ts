import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/components/AuthProvider';
import { toast } from 'sonner';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

interface OAuthIntegration {
  trigger_id: string;
  provider: string;
  name: string;
  is_active: boolean;
  workspace_name?: string;
  bot_name?: string;
  installed_at: string;
  created_at: string;
}

interface OAuthIntegrationStatus {
  agent_id: string;
  integrations: OAuthIntegration[];
}

interface OAuthInstallRequest {
  agent_id: string;
  provider: 'slack' | 'discord' | 'teams';
}

interface OAuthInstallResponse {
  install_url: string;
  provider: string;
}

const initiateOAuthInstall = async (request: OAuthInstallRequest, token: string | null): Promise<OAuthInstallResponse> => {
  if (!token) {
    throw new Error('You must be logged in to manage integrations');
  }
  
  const response = await fetch(`${API_URL}/integrations/install`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to initiate installation');
  }

  return response.json();
};

const uninstallOAuthIntegration = async (triggerId: string, token: string | null): Promise<void> => {
  if (!token) {
    throw new Error('You must be logged in to manage integrations');
  }
  
  const response = await fetch(`${API_URL}/integrations/uninstall/${triggerId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to uninstall integration');
  }
};

export const useInstallOAuthIntegration = () => {
  const queryClient = useQueryClient();
  const { token } = useAuth();

  return useMutation({
    mutationFn: (request: OAuthInstallRequest) => initiateOAuthInstall(request, token),
    onSuccess: (data, variables) => {
      sessionStorage.setItem('oauth_agent_id', variables.agent_id);
      sessionStorage.setItem('oauth_provider', variables.provider);
      window.location.href = data.install_url;
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to start OAuth installation');
    },
  });
};

export const useUninstallOAuthIntegration = () => {
  const queryClient = useQueryClient();
  const { token } = useAuth();

  return useMutation({
    mutationFn: (triggerId: string) => uninstallOAuthIntegration(triggerId, token),
    onSuccess: (_, triggerId) => {
      toast.success('Integration uninstalled successfully');
      queryClient.invalidateQueries({ queryKey: ['oauth-integrations'] });
      queryClient.invalidateQueries({ queryKey: ['agent-triggers'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to uninstall integration');
    },
  });
};

export const useOAuthCallbackHandler = () => {
  const queryClient = useQueryClient();

  const handleCallback = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const agentId = sessionStorage.getItem('oauth_agent_id');
    const provider = sessionStorage.getItem('oauth_provider');
    
    const slackSuccess = urlParams.get('slack_success');
    const discordSuccess = urlParams.get('discord_success');
    const teamsSuccess = urlParams.get('teams_success');
    const triggerId = urlParams.get('trigger_id');
    const workspaceName = urlParams.get('workspace');
    const botName = urlParams.get('bot_name');

    const slackError = urlParams.get('slack_error');
    const discordError = urlParams.get('discord_error');
    const teamsError = urlParams.get('teams_error');

    if (slackSuccess || discordSuccess || teamsSuccess) {
      const providerName = slackSuccess ? 'Slack' : discordSuccess ? 'Discord' : 'Teams';
      toast.success(`${providerName} integration installed successfully!`);
      
      if (agentId) {
        queryClient.invalidateQueries({ queryKey: ['oauth-integrations', agentId] });
      }

      sessionStorage.removeItem('oauth_agent_id');
      sessionStorage.removeItem('oauth_provider');
      
      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);
    } else if (slackError || discordError || teamsError) {
      const error = slackError || discordError || teamsError;
      const providerName = slackError ? 'Slack' : discordError ? 'Discord' : 'Teams';
      toast.error(`Failed to install ${providerName} integration: ${error}`);
      
      sessionStorage.removeItem('oauth_agent_id');
      sessionStorage.removeItem('oauth_provider');
      
      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);
    }
  };

  return { handleCallback };
}; 