'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { FloatingToolPreview, ToolCallInput } from './floating-tool-preview';
import { isLocalMode } from '@/lib/config';

export interface ChatSnackProps {
    toolCalls?: ToolCallInput[];
    toolCallIndex?: number;
    onExpandToolPreview?: () => void;
    agentName?: string;
    showToolPreview?: boolean;
    subscriptionData?: any;
    onOpenUpgrade?: () => void;
    isVisible?: boolean;
}

const SNACK_LAYOUT_ID = 'chat-snack-float';
const SNACK_CONTENT_LAYOUT_ID = 'chat-snack-content';

export const ChatSnack: React.FC<ChatSnackProps> = ({
    toolCalls = [],
    toolCallIndex = 0,
    onExpandToolPreview,
    agentName,
    showToolPreview = false,
    subscriptionData,
    onOpenUpgrade,
    isVisible = false,
}) => {
    const [currentView, setCurrentView] = React.useState(0);
    // Billing removed - no upgrade notifications
    const notifications = [];

    if (showToolPreview && toolCalls.length > 0) {
        notifications.push('tool');
    }

    const totalNotifications = notifications.length;
    const hasMultiple = totalNotifications > 1;

    React.useEffect(() => {
        if (currentView >= totalNotifications && totalNotifications > 0) {
            setCurrentView(0);
        }
    }, [totalNotifications, currentView]);

    const shouldShowSnack = isVisible || (showToolPreview && toolCalls.length > 0);
    
    React.useEffect(() => {
        if (!hasMultiple || !shouldShowSnack) return;

        const interval = setInterval(() => {
            setCurrentView((prev) => (prev + 1) % totalNotifications);
        }, 20000);

        return () => clearInterval(interval);
    }, [hasMultiple, shouldShowSnack, totalNotifications, currentView]);
    
    if (!shouldShowSnack || totalNotifications === 0) return null;

    const currentNotification = notifications[currentView];

    const renderContent = () => {
        if (currentNotification === 'tool' && showToolPreview) {
            return (
                <FloatingToolPreview
                    toolCalls={toolCalls}
                    currentIndex={toolCallIndex}
                    onExpand={onExpandToolPreview || (() => { })}
                    agentName={agentName}
                    isVisible={true}
                    showIndicators={hasMultiple}
                    indicatorIndex={currentView}
                    indicatorTotal={totalNotifications}
                    onIndicatorClick={(index) => setCurrentView(index)}
                />
            );
        }

        // Billing removed - no upgrade notifications

        return null;
    };

    return (
        <div>
            {shouldShowSnack && renderContent()}
        </div>
    );
};
