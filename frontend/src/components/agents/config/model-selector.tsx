'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Check, Search, AlertTriangle, Crown, Cpu, Plus, Edit, Trash, KeyRound, Lock } from 'lucide-react';
import { AuroraLogo } from '@/components/sidebar/aurora-logo';
import { ModelProviderIcon } from '@/lib/model-provider-icons';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useModelSelection } from '@/hooks/agents';
import { formatModelName } from '@/stores/model-store';
import { isLocalMode } from '@/lib/config';
import { CustomModelDialog, CustomModelFormData } from '@/components/thread/chat-input/custom-model-dialog';
import Link from 'next/link';
import { toast } from 'sonner';

// Helper to render model labels with special styling for Kortix modes
const ModelLabel = ({ label, className }: { label: string; className?: string }) => {
    if (label === 'Kortix POWER Mode') {
        return (
            <span className={cn("flex items-center gap-2", className)}>
                <span className="font-medium">Kortix</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 dark:bg-primary/15 rounded-full">
                    <AuroraLogo size={12} variant="symbol" />
                    <span className="text-[11px] font-semibold tracking-wide uppercase text-primary">
                        Power
                    </span>
                </span>
            </span>
        );
    }
    if (label === 'Kortix Basic') {
        return (
            <span className={cn("flex items-center gap-2", className)}>
                <span className="font-medium">Kortix</span>
                <span className="text-xs font-medium text-muted-foreground px-1.5 py-0.5 bg-muted/50 rounded-md">
                    Basic
                </span>
            </span>
        );
    }
    return <span className={cn("font-medium", className)}>{label}</span>;
};

interface CustomModel {
  id: string;
  label: string;
}

interface AgentModelSelectorProps {
  value?: string;
  onChange: (model: string) => void;
  disabled?: boolean;
  variant?: 'default' | 'menu-item';
  className?: string;
}

export function AgentModelSelector({
  value,
  onChange,
  disabled = false,
  variant = 'default',
  className,
}: AgentModelSelectorProps) {
  const { 
    allModels, 
    canAccessModel, 
    subscriptionStatus,
    selectedModel: storeSelectedModel,
    handleModelChange: storeHandleModelChange,
    customModels: storeCustomModels,
    addCustomModel: storeAddCustomModel,
    updateCustomModel: storeUpdateCustomModel,
    removeCustomModel: storeRemoveCustomModel,
    modelsData // Now available directly from the hook
  } = useModelSelection();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  // Billing removed - always false
  const isFreeTier = false;
  
  const [isCustomModelDialogOpen, setIsCustomModelDialogOpen] = useState(false);
  const [dialogInitialData, setDialogInitialData] = useState<CustomModelFormData>({ id: '', label: '' });
  const [dialogMode, setDialogMode] = useState<'add' | 'edit'>('add');
  const [editingModelId, setEditingModelId] = useState<string | null>(null);

  const customModels = storeCustomModels;
  
  // Use the prop value if provided, otherwise fall back to store value
  const selectedModel = value || storeSelectedModel;

  const enhancedModelOptions = useMemo(() => {
    const modelMap = new Map();

    if (modelsData?.models) {
      modelsData.models.forEach(model => {
        const displayName = model.name || model.id;
        
        modelMap.set(model.id, {
          id: model.id, // Use the actual model ID
          label: displayName,
          requiresSubscription: false, // Billing removed - all models free
          priority: model.priority || 0,
          recommended: false, // Remove recommended badges since we commented out non-Anthropic models
          top: (model.priority || 0) >= 90,
          capabilities: model.capabilities || [],
          contextWindow: model.context_window || 128000,
          isCustom: false
        });
      });
    } else {
      // Fallback to allModels if API data not available
      allModels.forEach(model => {
        modelMap.set(model.id, {
          ...model,
          recommended: false, // Remove recommended badges
          isCustom: false
        });
      });
    }

    if (isLocalMode()) {
      customModels.forEach(model => {
        if (!modelMap.has(model.id)) {
          modelMap.set(model.id, {
            id: model.id,
            label: model.label || formatModelName(model.id),
            requiresSubscription: false,
            top: false,
            isCustom: true
          });
        } else {
          const existingModel = modelMap.get(model.id);
          modelMap.set(model.id, {
            ...existingModel,
            isCustom: true
          });
        }
      });
    }

    return Array.from(modelMap.values());
  }, [modelsData?.models, allModels, customModels]);
  
  const selectedModelDisplay = useMemo(() => {
    const model = enhancedModelOptions.find(m => m.id === selectedModel);
    return model?.label || selectedModel;
  }, [selectedModel, enhancedModelOptions]);

  const filteredOptions = useMemo(() => {
    return enhancedModelOptions.filter((opt) =>
      opt.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opt.id.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [enhancedModelOptions, searchQuery]);

  const sortedModels = useMemo(() => {
    // Billing removed - sort by priority only
    return [...filteredOptions].sort((a, b) => {
      return (b.priority ?? 0) - (a.priority ?? 0);
    });
  }, [filteredOptions]);

  // Billing removed - all models are accessible
  const allAccessibleModels = sortedModels; // All models are now accessible

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    } else {
      setSearchQuery('');
      setHighlightedIndex(-1);
    }
  }, [isOpen]);

  const handleSelect = (modelId: string) => {
    const isCustomModel = customModels.some(model => model.id === modelId);
    
    if (isCustomModel && isLocalMode()) {
      onChange(modelId);
      setIsOpen(false);
      return;
    }
    
    // Billing removed - all models are accessible
    const model = enhancedModelOptions.find(m => m.id === modelId);
    if (model) {
      onChange(modelId);
      setIsOpen(false);
    }
  };

  const handleSearchInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    e.stopPropagation();
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < filteredOptions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredOptions.length - 1
      );
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
      e.preventDefault();
      const selectedOption = filteredOptions[highlightedIndex];
      if (selectedOption) {
        handleSelect(selectedOption.id);
      }
    }
  };

  const openAddCustomModelDialog = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setDialogInitialData({ id: '', label: '' });
    setDialogMode('add');
    setIsCustomModelDialogOpen(true);
    setIsOpen(false);
  };

  const openEditCustomModelDialog = (model: CustomModel, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setDialogInitialData({ id: model.id, label: model.label });
    setEditingModelId(model.id);
    setDialogMode('edit');
    setIsCustomModelDialogOpen(true);
    setIsOpen(false);
  };

  const handleSaveCustomModel = (formData: CustomModelFormData) => {
    const modelId = formData.id.trim();
    const modelLabel = formData.label.trim() || formatModelName(modelId);

    if (!modelId) return;
    
    if (customModels.some(model =>
      model.id === modelId && (dialogMode === 'add' || model.id !== editingModelId))) {
      console.error('A model with this ID already exists');
      return;
    }

    closeCustomModelDialog();
    const newModel = { id: modelId, label: modelLabel };

    if (dialogMode === 'add') {
      storeAddCustomModel(newModel);
      onChange(modelId);
    } else {
      storeUpdateCustomModel(editingModelId!, newModel);
      if (selectedModel === editingModelId) {
        onChange(modelId);
      }
    }
    
    setIsOpen(false);
  };

  const closeCustomModelDialog = () => {
    setIsCustomModelDialogOpen(false);
    setDialogInitialData({ id: '', label: '' });
    setEditingModelId(null);
  };

  const handleDeleteCustomModel = (modelId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    e?.preventDefault();

    storeRemoveCustomModel(modelId);
    
    if (selectedModel === modelId) {
      // When deleting the currently selected custom model, let the hook determine the new default
      const firstAvailableModel = allModels.find(m => canAccessModel(m.id));
      if (firstAvailableModel) {
        onChange(firstAvailableModel.id);
      }
    }
  };

  const renderModelOption = (model: any, index: number) => {
    const isCustom = Boolean(model.isCustom) || 
      (isLocalMode() && customModels.some(m => m.id === model.id));
    const accessible = true; // Billing removed - all models accessible
    const isHighlighted = index === highlightedIndex;
    const isPremium = model.requiresSubscription;
    const isLowQuality = false; // API models are quality controlled
    const isRecommended = false; // Remove recommended badges
    const isPowerModel = model.id === 'kortix/power';

    // Format cost display
    const formatCost = (cost: number | null | undefined) => {
      if (cost === null || cost === undefined) return null;
      return `$${cost.toFixed(2)}`;
    };

    const inputCost = formatCost(model.inputCostPerMillionTokens);
    const outputCost = formatCost(model.outputCostPerMillionTokens);

    return (
      <Tooltip key={`model-${model.id}-${index}`}>
        <TooltipTrigger asChild>
            <div className='w-full'>
              <DropdownMenuItem
                className={cn(
                  "text-sm px-2 py-2 mx-2 my-0.5 flex items-center gap-0 rounded-lg transition-all duration-200",
                  accessible ? "cursor-pointer" : "cursor-not-allowed",
                  isHighlighted && accessible && "bg-accent",
                  selectedModel === model.id && accessible && "bg-muted border border-border",
                  !accessible && !disabled && "opacity-60 hover:opacity-70"
                )}
                onClick={() => !disabled && handleSelect(model.id)}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className={cn("relative", !accessible && "opacity-60")}>
                  <ModelProviderIcon modelId={model.id} size={24} />
                  </div>
                  <div className={cn("flex-1", !accessible && "opacity-60")}>
                    <ModelLabel label={model.label} className={!accessible ? "opacity-60" : ""} />
                  </div>
                </div>
                <div className={cn("w-16 text-right text-xs text-muted-foreground", !accessible && "opacity-60")}>
                  {inputCost || '—'}
                </div>
                <div className={cn("w-16 text-right text-xs text-muted-foreground", !accessible && "opacity-60")}>
                  {outputCost || '—'}
                </div>
                <div className="w-8 flex items-center justify-center">
                  {isLowQuality && (
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                  )}
                  {isLocalMode() && isCustom && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditCustomModelDialog(model, e);
                        }}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <Edit className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCustomModel(model.id, e);
                        }}
                        className="text-muted-foreground hover:text-red-500"
                      >
                        <Trash className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </DropdownMenuItem>
            </div>
          </TooltipTrigger>
          {isLowQuality ? (
            <TooltipContent side="left" className="text-xs max-w-xs">
              <p>Not recommended for complex tasks</p>
            </TooltipContent>
          ) : isCustom ? (
            <TooltipContent side="left" className="text-xs max-w-xs">
              <p>Custom model</p>
            </TooltipContent>
          ) : null}
        </Tooltip>
    );
  };

  return (
    <div className="relative">
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <Tooltip>
          <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild disabled={disabled}>
                {variant === 'menu-item' ? (
                  <div
                    className={cn(
                      "flex items-center justify-between cursor-pointer rounded-lg px-3 py-2 mx-0 my-0.5 text-sm hover:bg-accent",
                      disabled && "opacity-50 cursor-not-allowed",
                      className
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <ModelProviderIcon 
                        modelId={selectedModel} 
                        size={24}
                      />
                      <span className="truncate"><ModelLabel label={selectedModelDisplay} /></span>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className={cn(
                      "h-8 px-4 py-2",
                      disabled && "opacity-50 cursor-not-allowed",
                      className
                    )}
                  >
                    <ModelProviderIcon modelId={selectedModel} size={24} />
                    <span className="text-sm"><ModelLabel label={selectedModelDisplay} /></span>
                  </Button>
                )}
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side={variant === 'menu-item' ? 'left' : 'top'} className="text-xs">
              <p>Choose a model for this agent</p>
            </TooltipContent>
        </Tooltip>
        <DropdownMenuContent
          align={variant === 'menu-item' ? 'end' : 'start'}
          className="w-80 p-0 overflow-hidden"
          sideOffset={variant === 'menu-item' ? 8 : 4}
        >
          <div className="max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700 scrollbar-track-transparent w-full">
            <div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-muted-foreground p-2 px-4">All Models</span>
                {isLocalMode() && (
                  <div className="flex items-center gap-1 p-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                          <Link
                            href="/settings/env-manager"
                            className="h-6 w-6 p-0 flex items-center justify-center"
                          >
                            <KeyRound className="h-3.5 w-3.5" />
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="text-xs">
                          Local .Env Manager
                        </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={(e) => {
                              e.stopPropagation();
                              openAddCustomModelDialog(e);
                            }}
                          >
                            <Plus className="h-3.5 w-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="text-xs">
                          Add a custom model
                        </TooltipContent>
                    </Tooltip>
                  </div>
                )}
              </div>
              <div className="px-1 py-1">
                <div className="relative px-1 flex items-center">
                  <Search className="absolute left-3 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="Search models..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleSearchInputKeyDown}
                    className="w-full h-8 px-8 py-1 rounded-lg text-sm focus:outline-none bg-muted"
                  />
                </div>
              </div>
              
              {/* Pricing Header */}
              <div className="px-2 py-2">
                <div className="flex items-center gap-0 text-xs text-muted-foreground">
                  <div className="flex-1 pl-2">Model</div>
                  <div className="w-16 text-right pr-2">Input</div>
                  <div className="w-16 text-right pr-2">Output</div>
                  <div className="w-8"></div>
                </div>
              </div>
              
              {/* Billing removed - show all models together */}
                <div>
                  {sortedModels.length > 0 ? (
                    sortedModels.map((model, index) => renderModelOption(model, index))
                  ) : (
                    <div className="text-sm text-center py-4 text-muted-foreground">
                      No models match your search
                    </div>
                  )}
                </div>
            </div>
            
            {/* Pricing Info Footer */}
            <div className="px-4 py-2 border-t border-border bg-muted/30">
              <div className="text-[10px] text-muted-foreground text-center">
                * All prices are per 1 million tokens
              </div>
            </div>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>
      {isLocalMode() && (
        <CustomModelDialog
          isOpen={isCustomModelDialogOpen}
          onClose={closeCustomModelDialog}
          onSave={handleSaveCustomModel}
          initialData={dialogInitialData}
          mode={dialogMode}
        />
      )}
    </div>
  );
}
