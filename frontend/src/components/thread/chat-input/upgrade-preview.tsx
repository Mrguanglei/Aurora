import React from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { isLocalMode } from '@/lib/config';
import { Button } from '@/components/ui/button';

export interface UpgradePreviewProps {
    subscriptionData?: any;
    onClose?: () => void;
    onOpenUpgrade?: () => void;
    hasMultiple?: boolean;
    showIndicators?: boolean;
    currentIndex?: number;
    totalCount?: number;
    onIndicatorClick?: (index: number) => void;
}

export const UpgradePreview: React.FC<UpgradePreviewProps> = () => {
    // Billing removed - component disabled
    return null;
};

