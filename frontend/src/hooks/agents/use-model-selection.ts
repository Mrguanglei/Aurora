'use client';

import React from 'react';
import { useModelStore } from '@/stores/model-store';
import { useCallback, useEffect, useMemo } from 'react';

export interface ModelOption {
  id: string;
  label: string;
  requiresSubscription: boolean;
  description?: string;
  priority?: number;
  recommended?: boolean;
  capabilities?: string[];
  contextWindow?: number;
}

// Billing removed - all models are free

// No automatic default model selection — frontend fetches available models from backend

export const useModelSelection = () => {
  const { selectedModel, setSelectedModel } = useModelStore();

  // Fetch available models from backend to reflect configured providers.
  const [availableModels, setAvailableModels] = React.useState<ModelOption[]>([]);
  const [isLoadingModels, setIsLoadingModels] = React.useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchModels = async () => {
      try {
        setIsLoadingModels(true);
        const res = await fetch('/models');
        if (!res.ok) throw new Error('Failed to fetch models');
        const data = await res.json();
        if (!mounted) return;
        const mapped: ModelOption[] = (data || []).map((m: any) => ({
          id: m.id,
          label: m.label,
          requiresSubscription: false,
          priority: 1,
          recommended: false,
          capabilities: m.capabilities || ['chat'],
          contextWindow: m.contextWindow || 128000,
          // include configured flag for UI
          ...(m.configured === false ? { recommended: false } : {})
        }));
        setAvailableModels(mapped);
      } catch (e) {
        console.error('Failed to load models', e);
        // Fallback to default two models if fetch fails
        setAvailableModels([
          { id: 'doubao/doubao-seed-1-6-251015', label: 'Doubao (豆包)', requiresSubscription: false, priority: 1, recommended: true, capabilities: ['chat'], contextWindow: 200000 },
          { id: 'openrouter/deepseek/deepseek-chat', label: 'DeepSeek Chat', requiresSubscription: false, priority: 2, recommended: false, capabilities: ['chat'], contextWindow: 128000 },
        ]);
      } finally {
        setIsLoadingModels(false);
      }
    };
    fetchModels();
    return () => { mounted = false; };
  }, []);

  // All models are accessible - billing removed
  const accessibleModels = useMemo(() => availableModels, [availableModels]);

  // Initialize selected model when data loads
  // Note: do NOT auto-select a model. User must pick a model explicitly in the UI.
  // This keeps selection manual (no automatic defaulting).

  const handleModelChange = useCallback((modelId: string) => {
    const model = accessibleModels.find(m => m.id === modelId);
    if (model) {
      console.log('🔧 useModelSelection: Changing model to:', modelId);
      setSelectedModel(modelId);
    }
  }, [accessibleModels, setSelectedModel]);

  // Billing removed - subscription always active
  const subscriptionStatus = 'active' as const;

  // Stable callback for checking model access - all models accessible now
  const canAccessModel = useCallback((modelId: string) => {
    // Billing removed - all models are accessible
    const model = availableModels.find(m => m.id === modelId);
    return !!model;
  }, [availableModels]);

  // Stable callback for checking subscription requirement - always false now
  const isSubscriptionRequired = useCallback((modelId: string) => {
    return false; // No subscription required - billing removed
  }, []);

  // Stable callback for getting actual model ID
  const getActualModelId = useCallback((modelId: string) => modelId, []);

  // Stable no-op callbacks for custom models (not implemented)
  const refreshCustomModels = useCallback(() => {}, []);
  const addCustomModel = useCallback((_model: any) => {}, []);
  const updateCustomModel = useCallback((_id: string, _model: any) => {}, []);
  const removeCustomModel = useCallback((_id: string) => {}, []);

  return {
    selectedModel,
    setSelectedModel: handleModelChange,
    availableModels: accessibleModels,
    allModels: availableModels,
    isLoading: isLoadingModels,
    modelsData: undefined,
    subscriptionStatus,
    canAccessModel,
    isSubscriptionRequired,
    handleModelChange,
    customModels: [] as any[],
    addCustomModel,
    updateCustomModel,
    removeCustomModel,
    getActualModelId,
    refreshCustomModels,
  };
};
