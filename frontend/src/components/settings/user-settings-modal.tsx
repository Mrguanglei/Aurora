'use client';

import * as React from 'react';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
    Settings,
    CreditCard,
    KeyRound,
    X,
    Trash2,
    TrendingDown,
    ExternalLink,
    Info,
    FileText,
    Plug,
    Bell,
    Mail,
    Smartphone,
    AppWindow,
    Key,
    Camera,
    Loader2,
    Upload,
    Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { isLocalMode, isProductionMode } from '@/lib/config';
import { backendApi } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Switch } from '@/components/ui/switch';
import { LocalEnvManager } from '@/components/env-manager/local-env-manager';
import { useIsMobile } from '@/hooks/utils';
import { SpotlightCard } from '@/components/ui/spotlight-card';
import { useQueryClient } from '@tanstack/react-query';
import { 
    useAccountDeletionStatus, 
    useRequestAccountDeletion, 
    useCancelAccountDeletion,
    useDeleteAccountImmediately
} from '@/hooks/account/use-account-deletion';
import { useAuth } from '@/components/AuthProvider';
import { useAccounts } from '@/hooks/account';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Zap,
    AlertTriangle,
    Shield,
    CheckCircle,
    RotateCcw,
    Clock,
    Infinity,
    ShoppingCart,
    Lightbulb,
    CalendarClock,
    ArrowRight
} from 'lucide-react';
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { formatCredits } from '@/lib/utils/credit-formatter';
import { LanguageSwitcher } from './language-switcher';
import { useTranslations } from 'next-intl';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { MemorySettings } from '@/components/memory/MemorySettings';

type TabId = 'general' | 'usage' | 'memory' | 'env-manager' | 'knowledge-base' | 'integrations' | 'api-keys';

interface Tab {
    id: TabId;
    label: string;
    icon: React.ElementType;
    disabled?: boolean;
}

interface UserSettingsModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void; 
    defaultTab?: TabId;
    returnUrl?: string;
}

export function UserSettingsModal({
    open,
    onOpenChange,
    defaultTab = 'general',
    returnUrl = typeof window !== 'undefined' ? window?.location?.href || '/' : '/',
}: UserSettingsModalProps) {
    const router = useRouter();
    const isMobile = useIsMobile();
    const [activeTab, setActiveTab] = useState<TabId>(defaultTab);
    const isLocal = isLocalMode();
    const isProduction = isProductionMode();
    const tabs: Tab[] = [
        { id: 'general', label: 'General', icon: Settings },
        { id: 'usage', label: 'Usage', icon: TrendingDown },
        { id: 'memory', label: 'Memory', icon: Brain },
        { id: 'knowledge-base', label: 'Knowledge Base', icon: FileText },
        { id: 'integrations', label: 'Integrations', icon: Plug },
        { id: 'api-keys', label: 'API Keys', icon: Key },
        ...(isLocal ? [{ id: 'env-manager' as TabId, label: 'Env Manager', icon: KeyRound }] : []),
    ];
    
    useEffect(() => {
        setActiveTab(defaultTab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [defaultTab]);

    const handleTabClick = (tabId: TabId) => {
        if (tabId === 'knowledge-base') {
            // Close modal first for instant feel, then navigate
            onOpenChange(false);
            router.push('/knowledge');
        } else if (tabId === 'integrations') {
            onOpenChange(false);
            router.push('/settings/credentials');
        } else if (tabId === 'api-keys') {
            onOpenChange(false);
            router.push('/settings/api-keys');
        } else {
            setActiveTab(tabId);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                className={cn(
                    "p-0 gap-0",
                    isMobile 
                        ? "fixed inset-0 w-screen h-screen max-w-none max-h-none rounded-none m-0 translate-x-0 translate-y-0 left-0 top-0" 
                        : "max-w-6xl max-h-[90vh] overflow-hidden"
                )}
                hideCloseButton={true}
            >
                <DialogTitle className="sr-only">Settings</DialogTitle>
                
                {isMobile ? (
                    /* Mobile Layout - Full Screen */
                    <div className="flex flex-col h-screen w-screen overflow-hidden">
                        {/* Mobile Header */}
                        <div className="px-4 py-3 border-b border-border flex-shrink-0 bg-background">
                            <div className="flex items-center justify-between">
                                <div className="text-lg font-semibold">Settings</div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => onOpenChange(false)}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                        
                        {/* Mobile Tabs - Horizontal Scroll */}
                        <div className="px-3 py-2.5 border-b border-border flex-shrink-0 bg-background">
                            <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-3 px-3 scrollbar-none [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                                {tabs.map((tab) => {
                                    const Icon = tab.icon;
                                    const isActive = activeTab === tab.id;

                                    return (
                                        <button
                                            key={tab.id}
                                            onClick={() => handleTabClick(tab.id)}
                                            disabled={tab.disabled}
                                            className={cn(
                                                "flex items-center gap-2 px-3 py-2 text-sm rounded-lg whitespace-nowrap flex-shrink-0 transition-colors",
                                                isActive
                                                    ? "bg-muted text-foreground font-medium"
                                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                            )}
                                        >
                                            <Icon className="h-4 w-4 flex-shrink-0" />
                                            <span>{tab.label}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        
                        {/* Mobile Content - Scrollable */}
                        <div className="flex-1 overflow-x-hidden overflow-y-auto">
                            <div className="w-full max-w-full">
                                {activeTab === 'general' && <GeneralTab onClose={() => onOpenChange(false)} />}
                                {activeTab === 'usage' && <UsageTab />}
                                {activeTab === 'memory' && <MemorySettings />}
                                {activeTab === 'env-manager' && isLocal && <EnvManagerTab />}
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Desktop Layout - Side by Side */
                    <div className="flex flex-row h-[700px]">
                        {/* Desktop Sidebar */}
                        <div className="bg-background flex-shrink-0 w-56 p-4 border-r border-border">
                            <div className="flex justify-start mb-3">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => onOpenChange(false)}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            </div>
                            
                            {/* Desktop Tabs */}
                            <div className="flex flex-col gap-1.5">
                                {tabs.map((tab) => {
                                    const Icon = tab.icon;
                                    const isActive = activeTab === tab.id;

                                    return (
                                        <button
                                            key={tab.id}
                                            onClick={() => handleTabClick(tab.id)}
                                            disabled={tab.disabled}
                                            className={cn(
                                                "w-full flex items-center gap-3 px-4 py-3 text-sm rounded-lg transition-colors",
                                                isActive
                                                    ? "bg-muted text-foreground"
                                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                            )}
                                        >
                                            <Icon className="h-4 w-4 flex-shrink-0" />
                                            <span>{tab.label}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        
                        {/* Desktop Content */}
                        <div className="flex-1 overflow-y-auto min-h-0 w-full max-w-full">
                            {activeTab === 'general' && <GeneralTab onClose={() => onOpenChange(false)} />}
                            {activeTab === 'usage' && <UsageTab />}
                            {activeTab === 'memory' && <MemorySettings />}
                            {activeTab === 'env-manager' && isLocal && <EnvManagerTab />}
                        </div>
                    </div>
                )}

            </DialogContent>
        </Dialog>
    );
}


function GeneralTab({ onClose }: { onClose: () => void }) {
    const t = useTranslations('settings.general');
    const tCommon = useTranslations('common');
    const [userName, setUserName] = useState('');
    const [userEmail, setUserEmail] = useState('');
    const [avatarUrl, setAvatarUrl] = useState('');
    const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
    const [avatarFile, setAvatarFile] = useState<File | null>(null);
    const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [showCancelDialog, setShowCancelDialog] = useState(false);
    const [deleteConfirmText, setDeleteConfirmText] = useState('');
    const [deletionType, setDeletionType] = useState<'grace-period' | 'immediate'>('grace-period');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const { data: accounts } = useAccounts();

    const { data: deletionStatus, isLoading: isCheckingStatus } = useAccountDeletionStatus();
    const requestDeletion = useRequestAccountDeletion();
    const cancelDeletion = useCancelAccountDeletion();
    const deleteImmediately = useDeleteAccountImmediately();

    useEffect(() => {
        // Use accounts data from React Query (which auto-updates when invalidated)
        // Use the same logic as sidebar-left.tsx to get personal account
        if (accounts && accounts.length > 0) {
            const personalAccount = (accounts.find((account: any) => account.personal_account) || accounts[0]) as any;
            // Always update from accounts data when it's available
            setUserName(personalAccount.username || personalAccount.email?.split('@')[0] || '');
            setUserEmail(personalAccount.email || '');
            setAvatarUrl(personalAccount.avatar_url || '');
            setIsLoading(false);
        } else if (user && (!accounts || accounts.length === 0)) {
            // Fallback to AuthProvider data if accounts not loaded yet or empty
            setUserName(user.username || user.email?.split('@')[0] || '');
            setUserEmail(user.email || '');
            setIsLoading(false);
        }
    }, [accounts, user]);

    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map(part => part[0])
            .join('')
            .toUpperCase()
            .slice(0, 2) || 'U';
    };

    const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                toast.error(t('profilePicture.invalidType'));
                return;
            }
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                toast.error(t('profilePicture.tooLarge'));
                return;
            }
            setAvatarFile(file);
            const previewUrl = URL.createObjectURL(file);
            setAvatarPreview(previewUrl);
        }
    };

    const uploadAvatar = async (userId: string): Promise<string | null> => {
        if (!avatarFile) return avatarUrl;

        setIsUploadingAvatar(true);
        try {
            const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';
            const token = typeof window !== 'undefined' ? localStorage.getItem('auth-token') : null;
            const authToken = token ? JSON.parse(token)?.access_token : null;

            if (!authToken) {
                throw new Error('No authentication token found');
            }

            const formData = new FormData();
            formData.append('file', avatarFile);

            const response = await fetch(`${API_URL}/account/avatar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to upload avatar');
            }

            const result = await response.json();
            return result.avatar_url || null;
        } catch (error) {
            console.error('Avatar upload failed:', error);
            toast.error(error instanceof Error ? error.message : t('profilePicture.uploadFailed'));
            return null;
        } finally {
            setIsUploadingAvatar(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            if (!user?.id) throw new Error('User not found');

            // Upload avatar if a new one was selected
            let newAvatarUrl = avatarUrl;
            if (avatarFile) {
                const uploadedUrl = await uploadAvatar(user.id);
                if (uploadedUrl) {
                    newAvatarUrl = uploadedUrl;
                }
            }

            // Update user profile via backend API
            const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';
            const token = typeof window !== 'undefined' ? localStorage.getItem('auth-token') : null;
            const authToken = token ? JSON.parse(token)?.access_token : null;

            const response = await fetch(`${API_URL}/account/profile`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}),
                },
                body: JSON.stringify({
                    username: userName,
                    avatar_url: newAvatarUrl,  // 如果上传了新头像，更新 avatar_url
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to update profile');
            }

            const updatedUser = await response.json();
            
            // Invalidate accounts query to refresh avatar in sidebar
            queryClient.invalidateQueries({ queryKey: ['accounts'] });
            
            // Update local state
            toast.success(t('profileUpdateSuccess'));

            // Clean up preview URL
            if (avatarPreview) {
                URL.revokeObjectURL(avatarPreview);
                setAvatarPreview(null);
            }
            setAvatarFile(null);
            setAvatarUrl(newAvatarUrl);

        } catch (error) {
            console.error('Error updating profile:', error);
            toast.error(error instanceof Error ? error.message : t('profileUpdateFailed'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleRequestDeletion = async () => {
        if (deletionType === 'immediate') {
            await deleteImmediately.mutateAsync();
        } else {
            await requestDeletion.mutateAsync('User requested deletion');
        }
        setShowDeleteDialog(false);
        setDeleteConfirmText('');
        setDeletionType('grace-period'); // Reset to default
    };

    const handleCancelDeletion = async () => {
        await cancelDeletion.mutateAsync();
        setShowCancelDialog(false);
    };

    const formatDate = (dateString: string | null) => {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    if (isLoading) {
        return (
            <div className="p-4 sm:p-6 space-y-5 sm:space-y-6 min-w-0 max-w-full">
                <Skeleton className="h-8 w-32" />
                <div className="space-y-4">
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 pb-12 sm:pb-6 space-y-5 sm:space-y-6 min-w-0 max-w-full overflow-x-hidden">
            <div>
                <h3 className="text-lg font-semibold mb-1">{t('title')}</h3>
                <p className="text-sm text-muted-foreground">
                    {t('description')}
                </p>
            </div>

            <div className="space-y-4">
                {/* Profile Picture Section */}
                <div className="space-y-3">
                    <Label>{t('profilePicture.title')}</Label>
                    <div className="flex items-center gap-4">
                        <div className="relative group">
                            <Avatar className="h-16 w-16 border-2 border-border">
                                <AvatarImage 
                                    src={avatarPreview || avatarUrl} 
                                    alt={userName} 
                                />
                                <AvatarFallback className="text-base bg-muted">
                                    {getInitials(userName)}
                                </AvatarFallback>
                            </Avatar>
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploadingAvatar}
                                className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                            >
                                {isUploadingAvatar ? (
                                    <Loader2 className="h-5 w-5 text-white animate-spin" />
                                ) : (
                                    <Camera className="h-5 w-5 text-white" />
                                )}
                            </button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleAvatarChange}
                                className="hidden"
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploadingAvatar}
                                className="w-full sm:w-auto"
                            >
                                <Upload className="h-4 w-4 mr-1.5" />
                                {t('profilePicture.upload')}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                {t('profilePicture.hint')}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="name">{t('name')}</Label>
                    <Input
                        id="name"
                        value={userName}
                        onChange={(e) => setUserName(e.target.value)}
                        placeholder={t('namePlaceholder')}
                        className="shadow-none"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="email">{t('email')}</Label>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Input
                                id="email"
                                value={userEmail}
                                disabled
                                className="bg-muted/50 cursor-not-allowed shadow-none"
                            />
                        </TooltipTrigger>
                        <TooltipContent>
                            {t('emailCannotChange')}
                        </TooltipContent>
                    </Tooltip>
                </div>

                <div className="space-y-2">
                    <LanguageSwitcher />
                </div>
            </div>

            <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-4">
                <Button
                    variant="outline"
                    onClick={onClose}
                    className="w-full sm:w-auto"
                >
                    {tCommon('cancel')}
                </Button>
                <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="w-full sm:w-auto"
                >
                    {isSaving ? tCommon('saving') : t('saveChanges')}
                </Button>
            </div>

            {!isLocalMode() && (
                <>
                    <div className="pt-8 space-y-4">
                        <div>
                            <h3 className="text-base font-medium mb-1">{t('deleteAccount.title')}</h3>
                            <p className="text-sm text-muted-foreground">
                                {t('deleteAccount.description')}
                            </p>
                        </div>

                        {deletionStatus?.has_pending_deletion ? (
                            <Alert className="shadow-none border-amber-500/30 bg-amber-500/5">
                                <Clock className="h-4 w-4 text-amber-600" />
                                <AlertDescription>
                                    <div className="text-sm">
                                        <strong className="text-foreground">{t('deleteAccount.scheduled')}</strong>
                                        <p className="mt-1 text-muted-foreground">
                                            {t('deleteAccount.scheduledDescription', {
                                                date: formatDate(deletionStatus.deletion_scheduled_for)
                                            })}
                                        </p>
                                        <p className="mt-2 text-muted-foreground">
                                            {t('deleteAccount.canCancel')}
                                        </p>
                                    </div>
                                </AlertDescription>
                                <div className="mt-3">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setShowCancelDialog(true)}
                                        disabled={cancelDeletion.isPending}
                                    >
                                        {t('deleteAccount.cancelButton')}
                                    </Button>
                                </div>
                            </Alert>
                        ) : (
                            <Button
                                variant="outline"
                                onClick={() => setShowDeleteDialog(true)}
                                className="text-muted-foreground hover:text-foreground"
                            >
                                {t('deleteAccount.button')}
                            </Button>
                        )}
                    </div>

                    <Dialog open={showDeleteDialog} onOpenChange={(open) => {
                        setShowDeleteDialog(open);
                        if (!open) {
                            setDeleteConfirmText('');
                            setDeletionType('grace-period');
                        }
                    }}>
                        <DialogContent className="max-w-md max-h-[90vh] sm:max-h-[85vh] overflow-y-auto p-4 sm:p-6">
                            <DialogHeader>
                                <DialogTitle className="text-base sm:text-lg">{t('deleteAccount.dialogTitle')}</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                                <Alert className={cn(
                                    "shadow-none",
                                    deletionType === 'immediate' 
                                        ? "border-red-500/30 bg-red-500/5" 
                                        : "border-amber-500/30 bg-amber-500/5"
                                )}>
                                    <AlertTriangle className={cn(
                                        "h-4 w-4 flex-shrink-0",
                                        deletionType === 'immediate' ? "text-red-600" : "text-amber-600"
                                    )} />
                                    <AlertDescription>
                                        <strong className="text-foreground text-sm sm:text-base">
                                            {deletionType === 'immediate' 
                                                ? t('deleteAccount.warningImmediate')
                                                : t('deleteAccount.warningGracePeriod')}
                                        </strong>
                                    </AlertDescription>
                                </Alert>
                                
                                <div>
                                    <p className="text-sm font-medium mb-2">
                                        {t('deleteAccount.whenDelete')}
                                    </p>
                                    <ul className="text-xs sm:text-sm text-muted-foreground space-y-1.5 pl-4 sm:pl-5 list-disc">
                                        <li>{t('deleteAccount.agentsDeleted')}</li>
                                        <li>{t('deleteAccount.threadsDeleted')}</li>
                                        <li>{t('deleteAccount.credentialsRemoved')}</li>
                                        <li>{t('deleteAccount.subscriptionCancelled')}</li>
                                        <li>{t('deleteAccount.billingRemoved')}</li>
                                        {deletionType === 'grace-period' && (
                                            <li>{t('deleteAccount.scheduled30Days')}</li>
                                        )}
                                    </ul>
                                </div>

                                <div className="space-y-3">
                                    <Label className="text-sm">{t('deleteAccount.chooseDeletionType')}</Label>
                                    <RadioGroup value={deletionType} onValueChange={(value) => setDeletionType(value as 'grace-period' | 'immediate')}>
                                        <div className="flex items-start gap-2 sm:gap-3 rounded-md border p-3 sm:p-4">
                                            <RadioGroupItem value="grace-period" id="grace-period" className="mt-0.5 flex-shrink-0" />
                                            <div className="space-y-1 flex-1 min-w-0">
                                                <Label htmlFor="grace-period" className="font-medium cursor-pointer text-sm sm:text-base block">
                                                    {t('deleteAccount.gracePeriodOption')}
                                                </Label>
                                                <p className="text-xs sm:text-sm text-muted-foreground">
                                                    {t('deleteAccount.gracePeriodDescription')}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-2 sm:gap-3 rounded-md border border-red-500/30 p-3 sm:p-4">
                                            <RadioGroupItem value="immediate" id="immediate" className="mt-0.5 flex-shrink-0" />
                                            <div className="space-y-1 flex-1 min-w-0">
                                                <Label htmlFor="immediate" className="font-medium cursor-pointer text-sm sm:text-base text-red-600 block">
                                                    {t('deleteAccount.immediateOption')}
                                                </Label>
                                                <p className="text-xs sm:text-sm text-muted-foreground">
                                                    {t('deleteAccount.immediateDescription')}
                                                </p>
                                            </div>
                                        </div>
                                    </RadioGroup>
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="delete-confirm" className="text-sm">
                                        {t('deleteAccount.confirmText')}
                                    </Label>
                                    <Input
                                        id="delete-confirm"
                                        value={deleteConfirmText}
                                        onChange={(e) => setDeleteConfirmText(e.target.value)}
                                        placeholder={t('deleteAccount.confirmPlaceholder')}
                                        className="shadow-none text-sm sm:text-base"
                                        autoComplete="off"
                                    />
                                </div>
                                
                                <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-2">
                                    <Button variant="outline" onClick={() => {
                                        setShowDeleteDialog(false);
                                        setDeleteConfirmText('');
                                        setDeletionType('grace-period');
                                    }} className="w-full sm:w-auto">
                                        {t('deleteAccount.keepAccount')}
                                    </Button>
                                    <Button 
                                        variant="destructive" 
                                        onClick={handleRequestDeletion} 
                                        disabled={
                                            (requestDeletion.isPending || deleteImmediately.isPending) || 
                                            deleteConfirmText !== 'delete'
                                        }
                                        className="w-full sm:w-auto"
                                    >
                                        {(requestDeletion.isPending || deleteImmediately.isPending) 
                                            ? tCommon('processing') 
                                            : t('deleteAccount.button')}
                                    </Button>
                                </div>
                            </div>
                        </DialogContent>
                    </Dialog>

                    <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
                        <AlertDialogContent className="max-w-md p-4 sm:p-6">
                            <AlertDialogHeader>
                                <AlertDialogTitle className="text-base sm:text-lg">{t('deleteAccount.cancelDeletionTitle')}</AlertDialogTitle>
                            </AlertDialogHeader>
                            <div className="space-y-4">
                                <p className="text-xs sm:text-sm text-muted-foreground">
                                    {t('deleteAccount.cancelDeletionDescription')}
                                </p>
                                <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-2">
                                    <Button variant="outline" onClick={() => setShowCancelDialog(false)} className="w-full sm:w-auto">
                                        {tCommon('back')}
                                    </Button>
                                    <Button 
                                        onClick={handleCancelDeletion} 
                                        disabled={cancelDeletion.isPending}
                                        className="w-full sm:w-auto"
                                    >
                                        {cancelDeletion.isPending ? tCommon('processing') : t('deleteAccount.cancelDeletion')}
                                    </Button>
                                </div>
                            </div>
                        </AlertDialogContent>
                    </AlertDialog>
                </>
            )}
        </div>
    );
}

interface NotificationToggleProps {
    icon: React.ElementType;
    label: string;
    description: string;
    enabled: boolean;
    onToggle: (value: boolean) => void;
}

function NotificationToggle({ icon: Icon, label, description, enabled, onToggle }: NotificationToggleProps) {
    return (
        <div className="flex items-start justify-between gap-4 py-3 border-b last:border-0">
            <div className="flex items-start gap-3 flex-1">
                <Icon className="w-4 h-4 text-muted-foreground mt-0.5" />
                <div className="space-y-0.5 flex-1">
                    <Label htmlFor={label} className="text-sm font-medium cursor-pointer">
                        {label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                        {description}
                    </p>
                </div>
            </div>
            <Switch
                id={label}
                checked={enabled}
                onCheckedChange={onToggle}
            />
        </div>
    );
}

function UsageTab() {
        return (
            <div className="p-4 sm:p-6 space-y-5 sm:space-y-6 min-w-0 max-w-full overflow-x-hidden">
        <div className="text-sm text-muted-foreground">Usage information is not available.</div>
        </div>
    );
}

function CreditsHelpAlert() {
  return (
    <Alert>
      <AlertDescription>
        <div className="flex items-center">
          <Info className="h-4 w-4" />
          <Button
            variant="link"
            size="sm"
            className="h-7 text-muted-foreground"
            onClick={() => window.open('/help/credits', '_blank')}
          >
            Learn More about Credits
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}


function EnvManagerTab() {
    return (
        <div className="p-4 sm:p-6 min-w-0 max-w-full overflow-x-hidden">
            <LocalEnvManager />
        </div>
    );
}


