'use client';

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

const getDefaultModel = (accessibleModels: ModelOption[]): string => {
  // Pick the first accessible model (sorted by priority)
  // kortix/basic should be first for free users since power is not accessible
  const basicModel = accessibleModels.find(m => m.id === 'kortix/basic');
  if (basicModel) return basicModel.id;

  const powerModel = accessibleModels.find(m => m.id === 'kortix/power');
  if (powerModel) return powerModel.id;

  // Fallback: pick from accessible models sorted by priority
  if (accessibleModels.length > 0) {
    return accessibleModels[0].id;
  }

  return '';
};

export const useModelSelection = () => {
  const { selectedModel, setSelectedModel } = useModelStore();

  // Billing removed - use default models
  const availableModels = useMemo<ModelOption[]>(() => {
    // Default models - billing removed
    return [
      { id: 'kortix/basic', label: 'Kortix Basic', requiresSubscription: false, priority: 1, recommended: true },
      { id: 'kortix/power', label: 'Kortix Advanced Mode', requiresSubscription: false, priority: 2, recommended: true },
    ];
  }, []);

  // All models are accessible - billing removed
  const accessibleModels = useMemo(() => {
    return availableModels;
  }, [availableModels]);

  // Initialize selected model when data loads
  useEffect(() => {
    if (!accessibleModels.length) return;

    // If no model selected or selected model is not accessible, set a default
    const needsUpdate = !selectedModel ||
                        !accessibleModels.some(m => m.id === selectedModel);

    if (needsUpdate) {
      const defaultModelId = getDefaultModel(accessibleModels);
      if (defaultModelId && defaultModelId !== selectedModel) {
        console.log('🔧 useModelSelection: Setting default model:', defaultModelId);
        setSelectedModel(defaultModelId);
      }
    }
  }, [selectedModel, accessibleModels, setSelectedModel]);

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
    isLoading: false,
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
