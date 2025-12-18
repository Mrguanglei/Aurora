'use client';

import React, { useEffect, useState, Suspense, lazy } from 'react';
import { AppProviders } from '@/components/layout/app-providers';
import { useAuth } from '@/components/AuthProvider';

// Lazy load presentation modal (only needed when presentations are opened)
const PresentationViewerWrapper = lazy(() =>
  import('@/stores/presentation-viewer-store').then(mod => ({ default: mod.PresentationViewerWrapper }))
);

export function SharePageWrapper({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    const isLoggedIn = !!user;

    // If user is logged in, wrap with all necessary providers and show sidebar
    if (isLoggedIn) {
        return (
            <AppProviders showSidebar={true}>
                {children}
                <Suspense fallback={null}>
                    <PresentationViewerWrapper />
                </Suspense>
            </AppProviders>
        );
    }

    // Anon user: render children without sidebar or subscription sync (no auth required)
    return (
        <div className="flex-1">
            {children}
            <Suspense fallback={null}>
                <PresentationViewerWrapper />
            </Suspense>
        </div>
    );
}
